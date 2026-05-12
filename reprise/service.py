import random
from uuid import uuid4

from sqlalchemy.orm import Session

from reprise.agent import generate_cloze_deletions
from reprise.db import Reprisal
from reprise.repository import (
    ClozeDeletionRepository,
    MotifRepository,
    ReprisalRepository,
)


class Service:
    reprisal_count = 5

    def __init__(self, session: Session):
        self.session = session
        self.motif_repository = MotifRepository(session)
        self.reprisal_repository = ReprisalRepository(session)
        self.cloze_deletion_repository = ClozeDeletionRepository(session)

    def reprise(self) -> list[Reprisal]:
        motifs = self.motif_repository.get_motifs()
        if not motifs:
            return []
        reprisal_max = max([len(motif.reprisals) for motif in motifs])
        reprisal_min = min([len(motif.reprisals) for motif in motifs])

        reprisals = []
        set_uuid = uuid4()
        for motif in motifs:
            # randomly select from cloze deletions if available
            # this means that the algorithm will never return the original motif
            if motif.cloze_deletions:
                cloze_deletion = random.choice(motif.cloze_deletions)

            if len(motif.reprisals) < reprisal_max or reprisal_max == reprisal_min:
                reprisal = self.reprisal_repository.add_reprisal(
                    motif.uuid,
                    str(set_uuid),
                    cloze_deletion.uuid if motif.cloze_deletions else None,
                )
                self.session.refresh(motif)
                reprisals.append(reprisal)

                if len(reprisals) == self.reprisal_count:
                    break

        return reprisals

    def cloze_delete_motif(self, motif_uuid: str, n_max: int):
        """
        Create multiple cloze deletions for a motif.

        Args:
            motif_uuid: The UUID of the motif to create cloze deletions for
            n_max: The maximum number of different cloze deletion sets to generate

        Returns:
            List of created ClozeDeletion objects
        """
        motif = self.motif_repository.get_motif(motif_uuid)
        mask_tuples_sets = generate_cloze_deletions(content=motif.content, n_max=n_max)

        cloze_deletions = []
        for mask_tuples in mask_tuples_sets:
            cloze_deletion = self.cloze_deletion_repository.add_cloze_deletion(
                motif_uuid=motif_uuid, mask_tuples=mask_tuples
            )
            cloze_deletions.append(cloze_deletion)

        return cloze_deletions
