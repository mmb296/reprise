import logging
import re
from dataclasses import dataclass
from typing import List

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from reprise.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class MaskTuples(BaseModel):
    tuples: List[List[List[int]]] = Field(
        description="List of lists of [start, end] positions representing where to mask"
    )


system_prompt = """
You are a helpful assistant that creates cloze deletions for learning purposes.
Given a text, create an appropriate number of different cloze deletion sets (up to n_max sets) 
where each set masks different important words or phrases that are important to learn. For example,
think of this as making flashcards for the text. Make as many as appropriate to learn the important
information, but do not exceed n_max sets.

For example, for the text "George Washington was the first president":
{{
    "cloze_deletion_sets": [
    ["George Washington"],
    ["first"],
    ["president"]
    ]
}}
Note how the cloze deletions here represent important qualifiers on relevant information as well, i.e.
we did not choose "first president" but instead chose "first" and "president" separately.

Take these sets and call the find_word_indices function to get the mask_tuples.
"""


@dataclass
class OpenAIDependencies:
    api_key: str


agent = Agent(
    model="openai:gpt-4.1-mini",
    deps_type=OpenAIDependencies,
    system_prompt=system_prompt,
    output_type=MaskTuples,
)


@agent.tool
def find_word_indices(
    ctx: RunContext, text: str, words_to_mask: List[str]
) -> List[List[int]]:
    """
    Find the start and end indices of words to mask in the given text.

    Args:
        text: The text content to search in
        words_to_mask: List of words or phrases to find and mask

    Returns:
        List of [start, end] positions representing where to mask
    """
    indices = []
    for word in words_to_mask:
        # Unless there are special characters, use word boundaries to not match substrings
        if not re.search(r"[^\w\s]", word):
            pattern = r"\b" + re.escape(word) + r"\b"
            for match in re.finditer(pattern, text):
                start, end = match.span()
                indices.append([start, end - 1])
        else:
            pattern = re.escape(word)
            for match in re.finditer(pattern, text):
                start, end = match.span()
                indices.append([start, end - 1])

    # Sort by start index
    indices.sort(key=lambda x: x[0])

    if not indices:
        logger.warning(f"No matches found for words: {words_to_mask}")

    return indices


def generate_cloze_deletions(content: str, n_max: int = 1) -> List[List[List[int]]]:
    """
    Use AI to generate multiple cloze deletion sets.
    Returns a list of cloze deletion sets, each containing a list of [start, end]
    position pairs that define what should be masked.

    Args:
        content: The text content to generate cloze deletions for
        n_max: The maximum number of different cloze deletion sets to generate (default: 3)

    Returns:
        List of lists of [start, end] positions, where each inner list represents a cloze deletion set
    """

    response = agent.run_sync(
        f"Create appropriate cloze deletions (n_max={n_max}) for: '{content}'",
        deps=OpenAIDependencies(api_key=OPENAI_API_KEY),
    )
    return response.output.tuples
