"""
Implementation of the flexible character accuracy

Citation:
    Flexible character accuracy measure for reading-order-independent evaluation
    C. Clausner, S. Pletschacher, A. Antonacopoulos
    Pattern Recognition Letters, Volume 131, March 2020, Pages 390-397
Link: http://www.primaresearch.org/publications/PRL_Clausner_FlexibleCharacterAccuracy
DOI: https://doi.org/10.1016/j.patrec.2020.02.003

Note that we deviated from the original algorithm at some places.
"""

import sys
from collections import Counter
from functools import lru_cache, reduce
from itertools import product, takewhile
from typing import List, Tuple, Optional

from Levenshtein import editops
from multimethod import multimethod

from . import ExtractedText

if sys.version_info.minor == 5:
    from .flexible_character_accuracy_ds_35 import (
        PartVersionSpecific,
        Match,
        Distance,
        Coefficients,
    )
else:
    from .flexible_character_accuracy_ds import (
        PartVersionSpecific,
        Match,
        Distance,
        Coefficients,
    )


@multimethod
def flexible_character_accuracy(
    gt: ExtractedText, ocr: ExtractedText
) -> Tuple[float, List[Match]]:
    """Calculate the flexible character accuracy.

    Reference: contains steps 1-7 of the flexible character accuracy algorithm.

    :param gt: The ground truth ExtractedText object.
    :param ocr: The ExtractedText object to compare the ground truth with.
    :return: Score between 0 and 1 and match objects.
    """
    return flexible_character_accuracy(gt.text, ocr.text)


@multimethod
def flexible_character_accuracy(gt: str, ocr: str) -> Tuple[float, List[Match]]:
    """Calculate the flexible character accuracy.

    Reference: contains steps 1-7 of the flexible character accuracy algorithm.

    :param gt: The ground truth text.
    :param ocr: The text to compare the ground truth with.
    :return: Score between 0 and 1 and match objects.
    """

    best_score = -float("inf")
    best_matches = []
    # TODO: should this be configurable?
    combinations = product(
        range(15, 31, 5), range(0, 24, 3), range(0, 4, 1), range(0, 6, 1)
    )
    # TODO: place to parallelize the algorithm?
    for (edit_dist, length_diff, offset, length) in combinations:
        coef = Coefficients(
            edit_dist=edit_dist, length_diff=length_diff, offset=offset, length=length
        )
        # Steps 1 - 6 of the flexible character accuracy algorithm.
        matches = match_with_coefficients(gt, ocr, coef)
        # Step 7 of the flexible character accuracy algorithm.
        score = character_accuracy_for_matches(matches)
        if score > best_score:
            best_score = score
            best_matches = matches
        # early breaking: we only need one perfect fit
        if best_score >= 1:
            break
    return best_score, best_matches


def match_with_coefficients(gt: str, ocr: str, coef: Coefficients) -> List[Match]:
    """Match ground truth with ocr and consider a given set of coefficients.

    Reference: contains steps 1 - 6 of the flexible character accuracy algorithm.

    :return: A list of match objects to score and align the texts.
    """
    # Steps 1 and 2 of the flexible character accuracy algorithm.
    ocr_lines = initialize_lines(ocr)
    gt_lines = initialize_lines(gt)

    matches = []

    # Step 5 of the flexible character accuracy algorithm.
    while len(gt_lines) != 0 and len(ocr_lines) != 0:
        # Steps 3 and 4 of the flexible character accuracy algorithm.
        match = match_longest_gt_lines(gt_lines, ocr_lines, coef)
        if match:
            matches.append(match)

    # Step 6 of the flexible character accuracy algorithm.
    # remaining lines are considered as deletes and inserts
    deletes = [
        distance(line, Part(text="", line=line.line, start=line.start))
        for line in gt_lines
    ]
    inserts = [
        distance(Part(text="", line=line.line, start=line.start), line)
        for line in ocr_lines
    ]

    return [*matches, *deletes, *inserts]


def match_longest_gt_lines(
    gt_lines: List["Part"], ocr_lines: List["Part"], coef: Coefficients
) -> Optional[Match]:
    """Find the best match for the longest line(s) in ground truth.

    The longest lines in ground truth are matched against lines in ocr to find the
    best matching pair. This pair is then either considered a match on a full line
    or the line(s) is splitted and the non matching parts are added back to the list.

    Reference: contains steps 3 and 4 of the flexible character accuracy algorithm.

    :return: Possible match object.
    """
    best_score, best_match, best_gt, best_ocr = -float("inf"), None, None, None
    if not ocr_lines:
        return best_match

    # Step 3 of the flexible character accuracy algorithm (variation).
    # We do not only take the longest line from ground truth but decide on a length
    # threshold and take all lines from ground truth bigger than the threshold.
    length_threshold = min(gt_lines[0].length, ocr_lines[0].length) - 1
    for gt_line in takewhile(lambda line: line.length > length_threshold, gt_lines):
        match, ocr_line = match_gt_line(gt_line, ocr_lines, coef)
        score = -float("inf") if not match else character_accuracy(match.dist)
        if score > best_score:
            best_score, best_match, best_gt, best_ocr = score, match, gt_line, ocr_line
        # early breaking: we only need one perfect fit
        if best_score >= 1:
            break

    # Step 4 of the flexible character accuracy algorithm.
    if best_match:
        remove_or_split(best_gt, best_match.gt, gt_lines)
        remove_or_split(best_ocr, best_match.ocr, ocr_lines)

    return best_match


def match_gt_line(
    gt_line: "Part", ocr_lines: List["Part"], coef: Coefficients
) -> Tuple[Optional[Match], Optional["Part"]]:
    """Match the given ground truth line against all the lines in ocr.

    Reference: contains steps 3 of the flexible character accuracy algorithm.

    TODO: Make penalty function configurable?

    :return: Match object and the matched ocr line.
    """
    min_penalty = float("inf")
    best_match, best_ocr = None, None
    gt_line_length = gt_line.length
    gt_line_start = gt_line.start
    for ocr_line in ocr_lines:
        match = match_lines(gt_line, ocr_line)
        if match:
            penalty = calculate_penalty(
                gt_line_length,
                ocr_line.length,
                gt_line_start,
                ocr_line.start,
                match.gt.start,
                match.ocr.start,
                match.dist,
                coef,
            )
            if penalty < min_penalty:
                min_penalty, best_match, best_ocr = penalty, match, ocr_line
    return best_match, best_ocr


@lru_cache(maxsize=10000)
def match_lines(gt_line: "Part", ocr_line: "Part") -> Optional[Match]:
    """Matches two lines searching for a naive local alignment.

    The shorter line is moved along the longer line
    until the editing distance is minimized.

    Reference: see figure 2 in the doi:10.1016/j.patrec.2020.02.003.

    TODO: make distance function configurable?
    TODO: use @cache annotation in Python 3.9?

    :return: Match object if one is found.
    """
    min_length = min(gt_line.length, ocr_line.length)
    best_match = None
    best_i, best_j = 0, 0
    if min_length == 0:
        return best_match
    length_diff = gt_line.length - ocr_line.length
    min_edit_dist = float("inf")

    gt_parts = [
        (i, gt_line.substring(rel_start=i, rel_end=i + min_length))
        for i in range(0, max(1, length_diff + 1))
    ]
    ocr_parts = [
        (j, ocr_line.substring(rel_start=j, rel_end=j + min_length))
        for j in range(0, max(1, -1 * length_diff + 1))
    ]

    # add full line
    gt_parts = [*gt_parts, (0, gt_line)]
    ocr_parts = [*ocr_parts, (0, ocr_line)]

    for i, gt_part in gt_parts:
        for j, ocr_part in ocr_parts:
            match = distance(gt_part, ocr_part)
            edit_dist = score_edit_distance(match.dist)
            if edit_dist < min_edit_dist and match.dist.replace < min_length:
                min_edit_dist = edit_dist
                best_match = match
                best_i, best_j = i, j
    # elongate at the end for handling deletes
    if best_match and (best_match.dist.delete or best_match.dist.replace):
        part_length = best_match.gt.length
        additional_length = best_match.dist.delete + best_match.dist.replace
        for k in range(part_length + 1, part_length + additional_length + 1):
            match = distance(
                gt_line.substring(rel_start=best_i, rel_end=best_i + k),
                ocr_line.substring(rel_start=best_j, rel_end=best_j + k),
            )
            edit_dist = score_edit_distance(match.dist)
            if edit_dist < min_edit_dist and match.dist.replace < min_length:
                min_edit_dist = edit_dist
                best_match = match
    # is delete a better option?
    match = distance(gt_line, Part(text="", line=ocr_line.line, start=ocr_line.start))
    edit_dist = score_edit_distance(match.dist)
    if edit_dist < min_edit_dist:
        best_match = match

    return best_match


@lru_cache(maxsize=10000)
def distance(gt: "Part", ocr: "Part") -> Match:
    """Calculate the editing distance between the two lines.

    Using the already available `editops()` function with the Levenshtein distance.

    TODO: use @cache annotation in Python 3.9?
    TODO: wait for qurator-spk/dinglehopper#48 for efficient editops.

    :return: Match object containing the lines and the editing operations.
    """
    ops = editops(gt.text, ocr.text)
    edits = Counter([edit[0] for edit in ops])
    edits["match"] = gt.length - edits["delete"] - edits["replace"]
    return Match(gt=gt, ocr=ocr, dist=Distance(**edits), ops=ops)


def score_edit_distance(dist: Distance) -> int:
    """Calculate edit distance for a match.

    Formula: $deletes + inserts + 2 * replacements$

    :return: Sum of deletes, inserts and replacements.
    """
    return dist.delete + dist.insert + 2 * dist.replace


@lru_cache(10000)
def calculate_penalty(
    gt_length: int,
    ocr_length: int,
    gt_start: int,
    ocr_start: int,
    gt_match_start: int,
    ocr_match_start: int,
    dist: Distance,
    coef: Coefficients,
) -> float:
    """Calculate the penalty for a given match.

    For details and discussion see Section 3 in doi:10.1016/j.patrec.2020.02.003.

    :return: Penalty for the given match.
    """
    min_edit_dist = score_edit_distance(dist)
    length_diff = abs(gt_length - ocr_length)
    substring_length = min(gt_length, ocr_length)
    offset = 0.0
    if length_diff > 1:
        substring_pos = max(gt_match_start - gt_start, ocr_match_start - ocr_start)
        offset = length_diff / 2 - abs(substring_pos - length_diff / 2)
    return (
        min_edit_dist * coef.edit_dist
        + length_diff * coef.length_diff
        + offset * coef.offset
        - substring_length * coef.length
    )


def character_accuracy_for_matches(matches: List[Match]) -> float:
    """Character accuracy of a full text represented by a list of matches.

    See other `character_accuracy` for details.
    """
    agg = reduce(
        lambda acc, match: acc + Counter(match.dist._asdict()), matches, Counter()
    )  # type: Counter

    score = character_accuracy(Distance(**agg))
    return score


def character_accuracy(edits: Distance) -> float:
    """Character accuracy calculated by necessary edit operations.

    Edit operations are needed edits to transform one text into another.

    The character accuracy is given by $1 - errors / characters$.

    Errors are replacements, deletes and inserts.

    Note that it is possible to have more errors than characters in which case the
    character accuracy turns negative.

    Comparing two empty strings (having no edits) results in a character accuracy of 1.
    """
    errors = edits.replace + edits.delete + edits.insert
    chars = edits.match + edits.replace + edits.delete
    if not chars and not errors:
        # comparison of empty strings is considered a full match
        score = 1.0
    elif not chars:
        score = -errors
    else:
        score = 1.0 - errors / chars
    return score


def initialize_lines(text: str) -> List["Part"]:
    """Splits a text into lines and converts them to our line data object.

    The line objects are sorted by their length descending.

    Reference: contains steps 1 and 2 of the flexible character accuracy algorithm.

    :param text: Text to split into lines.
    :return: List of sorted line objects.
    """
    lines = [
        Part(text=line, line=i, start=0)
        for i, line in enumerate(text.splitlines())
        if len(line) > 0
    ]
    lines.sort(key=lambda x: x.length, reverse=True)
    return lines


def remove_or_split(original: "Part", match: "Part", lines: List["Part"]) -> bool:
    """Removes the matched line or splits it into parts.

    Reference: contains step 4 of the flexible character accuracy algorithm.

    :return: True if line was splitted.
    """
    splitted = False
    del lines[lines.index(original)]
    if match.length < original.length:
        lines.extend(original.split(match))
        # sorting for ocr is not mentioned in the paper, but is used as tie breaking =)
        lines.sort(key=lambda x: x.length, reverse=True)
        splitted = True
    return splitted


def split_matches(
    matches: List[Match], linesep="\n"
) -> Tuple[List[str], List[str], List[List]]:
    """Extracts text segments and editing operations in separate lists.

    :param matches: List of match objects.
    :param linesep: Character(s) or line separation.
    :return: List of ground truth segments, ocr segments and editing operations.
    """
    matches = sorted(matches, key=lambda m: m.gt.line + m.gt.start / 10000)
    line = 0
    gt, ocr, ops = [], [], []
    for match in matches:
        if match.gt.line > line:
            gt.append(linesep)
            ocr.append(linesep)
            ops.extend([[]] * len(linesep))
        line = match.gt.line
        gt.append(match.gt.text)
        ocr.append(match.ocr.text)
        ops.append(match.ops)
    return gt, ocr, ops


class Part(PartVersionSpecific):
    @property
    def end(self) -> int:
        return self.start + self.length

    @property
    def length(self) -> int:
        return len(self.text)

    def split(self, split: "Part") -> List["Part"]:
        """Split the line part by another and returns the remaining parts.

        `abc.split("b")` will return ´["a", "c"]`.

        :param split: The line part we want to use to split.
        :return: The parts before and after the split.
        """
        rest = []
        if self.start < split.start:
            rest.append(self.substring(rel_end=split.start - self.start))
        if split.end < self.end:
            rest.append(self.substring(rel_start=split.end - self.start))
        return rest

    def substring(self, rel_start: int = 0, rel_end: int = None) -> "Part":
        """Get part of the given line.

        Automatically handles the offset of the line.
        Therefore `substring(rel_start=2)` will return `Part[start+rel_start:]`.

        :param rel_start: start relative to the part of the line.
        :param rel_end: end relative to the part of the line.
        :return: Extracted part of the given part of the line.
        """
        text = self.text[rel_start:rel_end]
        start = self.start + rel_start
        return Part(line=self.line, text=text, start=start)
