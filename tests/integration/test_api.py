from unittest.mock import patch

import pytest

from reprise.agent import MaskTuples
from reprise.db import Citation, Motif, database_session
from tests.factories import citation_factory, cloze_deletion_factory, motif_factory


class TestAPI:
    @pytest.fixture
    def motif(self, session):
        return motif_factory(session=session).create()

    @pytest.fixture
    def citation(self, session):
        return citation_factory(session=session).create()

    @pytest.fixture
    def cloze_deletion(self, session, motif):
        return cloze_deletion_factory(session=session).create(motif=motif)

    # Common test data fixtures
    @pytest.fixture
    def motif_data(self):
        return {"content": "Test motif content"}

    @pytest.fixture
    def motif_with_citation_data(self):
        return {"content": "Test motif content", "citation": "Test citation"}

    @pytest.fixture
    def motif_with_auto_cloze_deletions_data(self):
        return {"content": "Test motif content", "auto_generate_cloze_deletions": True}

    @pytest.fixture
    def citation_data(self):
        return {"title": "Test citation title"}

    @pytest.fixture
    def cloze_deletion_data(self, motif):
        return {"motif_uuid": motif.uuid, "mask_tuples": [[0, 2], [4, 6]]}

    @pytest.fixture
    def cloze_update_data(self, cloze_deletion):
        return {"uuid": cloze_deletion.uuid, "mask_tuples": [[1, 3], [5, 7]]}

    def test_get_motifs(self, session, client):
        motif = motif_factory(session=session).create()
        cloze_deletion = cloze_deletion_factory(session=session).create(motif=motif)

        response = client.get("/motifs")
        data = json.loads(response.data)

        assert response.status_code == 200
        assert len(data["motifs"]) == 1
        assert data["motifs"][0]["content"] == motif.content
        assert data["motifs"][0]["cloze_deletions"] == [
            {"uuid": cloze_deletion.uuid, "mask_tuples": cloze_deletion.mask_tuples}
        ]

    def test_add_motif_without_citation(self, client, motif_data):
        response = client.post(
            "/motifs",
            data=json.dumps(motif_data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["content"] == motif_data["content"]
        assert data["citation"] is None
        assert data["cloze_deletions"] is None

        with database_session() as session:
            motif = session.query(Motif).filter_by(uuid=data["uuid"]).one_or_none()
            assert motif.content == motif_data["content"]

    def test_add_motif_with_citation(self, client, motif_with_citation_data):
        response = client.post(
            "/motifs",
            data=json.dumps(motif_with_citation_data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["content"] == motif_with_citation_data["content"]
        assert data["citation"] == motif_with_citation_data["citation"]
        assert data["cloze_deletions"] is None

        with database_session() as session:
            motif = session.query(Motif).filter_by(uuid=data["uuid"]).one_or_none()
            assert motif.content == motif_with_citation_data["content"]
            assert motif.citation.title == motif_with_citation_data["citation"]

    @patch("pydantic_ai.agent.Agent.run_sync")
    def test_add_motif_with_auto_cloze_deletions(
        self, mock_agent_run_sync, client, motif_with_auto_cloze_deletions_data
    ):
        # Mock the LLM response to return specific mask tuple sets
        mock_agent_run_sync.return_value.data = MaskTuples(
            tuples=[[[0, 3]], [[0, 3], [11, 17]]]
        )

        response = client.post(
            "/motifs",
            data=json.dumps(motif_with_auto_cloze_deletions_data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["cloze_deletions"] is not None
        assert len(data["cloze_deletions"]) == 2
        assert data["cloze_deletions"][0]["mask_tuples"] == [[0, 3]]
        assert data["cloze_deletions"][1]["mask_tuples"] == [[0, 3], [11, 17]]

        with database_session() as session:
            motif = session.query(Motif).filter_by(uuid=data["uuid"]).one_or_none()
            assert len(motif.cloze_deletions) == 2
            # The order might not be guaranteed, so check both ways
            mask_tuples_list = [cd.mask_tuples for cd in motif.cloze_deletions]
            assert [[0, 3]] in mask_tuples_list
            assert [[0, 3], [11, 17]] in mask_tuples_list

    def test_update_motif(self, client, motif, motif_data):
        response = client.put(
            f"/motifs/{motif.uuid}",
            data=json.dumps(motif_data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["content"] == motif_data["content"]

        with database_session() as session:
            motif = session.query(Motif).filter_by(uuid=motif.uuid).one_or_none()
            assert motif.content == motif_data["content"]

    def test_update_motif_invalid_citation(self, client, motif):
        response = client.put(
            f"/motifs/{motif.uuid}",
            data=json.dumps({"content": "Updated content", "citation": "invalid!"}),
            content_type="application/json",
        )

        assert response.status_code == 404

        with database_session() as session:
            motif = session.query(Motif).filter_by(uuid=motif.uuid).one_or_none()
            assert motif.content != "Updated content"

    def test_delete_motif(self, client, motif):
        response = client.delete(f"/motifs/{motif.uuid}")

        assert response.status_code == 200
        assert json.loads(response.data)["message"] == "Motif deleted"

        with database_session() as session:
            assert len(session.query(Motif).filter_by(uuid=motif.uuid).all()) == 0

    def test_create_citation(self, client, citation_data):
        response = client.post(
            "/citations",
            data=json.dumps(citation_data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["title"] == citation_data["title"]

        with database_session() as session:
            citation = (
                session.query(Citation).filter_by(uuid=data["uuid"]).one_or_none()
            )
            assert citation.title == citation_data["title"]

    def test_get_citations(self, client, citation):
        response = client.get("/citations")
        data = json.loads(response.data)

        assert response.status_code == 200
        assert len(data) == 1
        assert data[0]["title"] == citation.title

    def test_add_citation_to_motif(self, client, motif, citation):
        response = client.put(
            f"/motifs/{motif.uuid}",
            data=json.dumps({"content": motif.content, "citation": citation.title}),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["citation"] == citation.title

        with database_session() as session:
            motif = session.query(Motif).filter_by(uuid=motif.uuid).one_or_none()
            assert motif.citation.title == citation.title

    def test_reprise_motifs(self, session, client, motif):
        motif_2 = motif_factory(session=session).create()
        cloze_deletion = cloze_deletion_factory(session=session).create(motif=motif_2)

        response = client.post("/reprise")
        data = json.loads(response.data)

        assert response.status_code == 200
        assert len(data) > 0
        assert data[0]["content"] == motif.content
        assert data[0]["cloze_deletions"] is None
        assert data[1]["cloze_deletions"] == [
            {"uuid": cloze_deletion.uuid, "mask_tuples": cloze_deletion.mask_tuples}
        ]

    def test_get_motifs_paginated(self, client, session):
        motif_factory(session=session).create_batch(12)

        # first page
        response = client.get("/motifs?page=1&page_size=5")
        data = json.loads(response.data)
        assert response.status_code == 200
        assert len(data["motifs"]) == 5
        assert data["total_count"] == 12

        # second page
        response = client.get("/motifs?page=2&page_size=5")
        data = json.loads(response.data)
        assert response.status_code == 200
        assert len(data["motifs"]) == 5

        # third page
        response = client.get("/motifs?page=3&page_size=5")
        data = json.loads(response.data)
        assert response.status_code == 200
        assert len(data["motifs"]) == 2

        # empty page
        response = client.get("/motifs?page=4&page_size=5")
        data = json.loads(response.data)
        assert response.status_code == 200
        assert len(data["motifs"]) == 0

    def test_add_cloze_deletion(self, client, motif, cloze_deletion_data):
        response = client.post(
            "/cloze_deletions",
            data=json.dumps(cloze_deletion_data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["mask_tuples"] == cloze_deletion_data["mask_tuples"]

        with database_session() as session:
            motif = session.query(Motif).filter_by(uuid=motif.uuid).one_or_none()
            assert len(motif.cloze_deletions) == 1
            assert (
                motif.cloze_deletions[0].mask_tuples
                == cloze_deletion_data["mask_tuples"]
            )

    def test_update_cloze_deletion(
        self, client, motif, cloze_deletion, cloze_update_data
    ):
        response = client.put(
            "/cloze_deletions",
            data=json.dumps(cloze_update_data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data["mask_tuples"] == cloze_update_data["mask_tuples"]

        with database_session() as session:
            updated_cloze_deletion = (
                session.query(Motif)
                .filter_by(uuid=motif.uuid)
                .one_or_none()
                .cloze_deletions[0]
            )
            assert (
                updated_cloze_deletion.mask_tuples == cloze_update_data["mask_tuples"]
            )

    def test_delete_cloze_deletion(self, client, motif, cloze_deletion):
        response = client.delete(f"/cloze_deletions/{cloze_deletion.uuid}")
        assert response.status_code == 200
        assert json.loads(response.data)["message"] == "Cloze deletion deleted"

        with database_session() as session:
            assert (
                session.query(Motif)
                .filter_by(uuid=motif.uuid)
                .one_or_none()
                .cloze_deletions
                == []
            )

    # Parameterized validation tests
    @pytest.mark.parametrize(
        "endpoint,data,field,expected_status",
        [
            # Motif validation tests
            ("/motifs", {}, "content", 400),
            ("/motifs", {"content": 123}, "content", 400),
            # Citation validation tests
            ("/citations", {}, "title", 400),
            # Cloze deletion validation tests
            ("/cloze_deletions", {}, "motif_uuid", 400),
            ("/cloze_deletions", {}, "mask_tuples", 400),
            (
                "/cloze_deletions",
                {"motif_uuid": "uuid", "mask_tuples": "invalid"},
                "mask_tuples",
                400,
            ),
            (
                "/cloze_deletions",
                {"motif_uuid": "uuid", "mask_tuples": [[0], [4, 6]]},
                "mask_tuples",
                400,
            ),
            (
                "/cloze_deletions",
                {"motif_uuid": "uuid", "mask_tuples": [["a", "b"], [4, 6]]},
                "mask_tuples",
                400,
            ),
        ],
    )
    def test_validation_errors_post(
        self, client, endpoint, data, field, expected_status
    ):
        """Parameterized test for validation errors on POST endpoints."""
        response = client.post(
            endpoint,
            data=json.dumps(data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == expected_status
        if expected_status == 400:
            assert "validation_error" in data
            if field:
                # For flask-pydantic, errors are in body_params or query_params
                if "body_params" in data["validation_error"]:
                    errors = data["validation_error"]["body_params"]
                elif "query_params" in data["validation_error"]:
                    errors = data["validation_error"]["query_params"]
                else:
                    errors = []
                assert any(field in error["loc"] for error in errors)

    @pytest.mark.parametrize(
        "endpoint,data,field,expected_status",
        [
            # Motif update validation tests
            ("/motifs/some-uuid", {}, "content", 400),
            ("/motifs/some-uuid", {"content": 123}, "content", 400),
            (
                "/motifs/some-uuid",
                {"content": "valid", "citation": 123},
                "citation",
                400,
            ),
            # Cloze deletion update validation tests
            ("/cloze_deletions", {}, "uuid", 400),
            ("/cloze_deletions", {}, "mask_tuples", 400),
            (
                "/cloze_deletions",
                {"uuid": "some-uuid", "mask_tuples": "invalid"},
                "mask_tuples",
                400,
            ),
        ],
    )
    def test_validation_errors_put(
        self, client, endpoint, data, field, expected_status
    ):
        """Parameterized test for validation errors on PUT endpoints."""
        response = client.put(
            endpoint,
            data=json.dumps(data),
            content_type="application/json",
        )

        data = json.loads(response.data)
        assert response.status_code == expected_status
        if expected_status == 400:
            assert "validation_error" in data
            if field:
                # For flask-pydantic, errors are in body_params or query_params
                if "body_params" in data["validation_error"]:
                    errors = data["validation_error"]["body_params"]
                elif "query_params" in data["validation_error"]:
                    errors = data["validation_error"]["query_params"]
                else:
                    errors = []
                assert any(field in error["loc"] for error in errors)

    def test_malformed_json(self, client):
        """Test error handling for malformed JSON."""
        response = client.post(
            "/motifs",
            data="{invalid: json",
            content_type="application/json",
        )

        assert response.status_code == 400

    @patch("pydantic_ai.agent.Agent.run_sync")
    def test_add_motif_with_openai_error(
        self, mock_agent_run_sync, client, motif_with_auto_cloze_deletions_data
    ):
        # Mock the LLM call to raise an exception
        mock_agent_run_sync.side_effect = Exception("OpenAI API Error")

        response = client.post(
            "/motifs",
            data=json.dumps(motif_with_auto_cloze_deletions_data),
            content_type="application/json",
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "OpenAI API Error" in data["error"]
