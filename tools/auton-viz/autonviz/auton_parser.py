"""Extract ordered waypoint sequences from AutonCommandFactory.java.

For each public ``Command``-returning auton method, walk the body in source
order and collect the pose constants passed to ``resetOdometryFlipped(...)``
(the starting pose) and ``buildPathDeferred(...)`` (each driven waypoint).
"""

import re

from .pose_resolver import strip_java_comments

_METHOD_RE = re.compile(r"public\s+Command\s+(\w+)\s*\([^)]*\)\s*\{")
_WITH_NAME_RE = re.compile(r'\.withName\(\s*"([^"]*)"')
# A reset-odometry start pose, or a buildPathDeferred driven waypoint.
_CALL_RE = re.compile(
    r"resetOdometryFlipped\(\s*(?:FieldConstants\.)?(\w+)"
    r"|buildPathDeferred\(\s*(\w+)"
)


def _extract_braced_body(text, open_idx):
    """Return the substring from ``text[open_idx]`` (a '{') to its matching '}'."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx : i + 1]
    raise ValueError("unbalanced braces starting at %d" % open_idx)


def parse_autons(source):
    """Return ``{method_name: {"title": str, "waypoints": [{"name", "kind"}]}}``.

    Methods with no driven waypoints (helpers like ``buildPathDeferred`` or
    ``followWaypoints``) are excluded.
    """
    source = strip_java_comments(source)
    autos = {}
    for match in _METHOD_RE.finditer(source):
        name = match.group(1)
        body = _extract_braced_body(source, match.end() - 1)

        waypoints = []
        for call in _CALL_RE.finditer(body):
            if call.group(1) is not None:
                waypoints.append({"name": call.group(1), "kind": "start"})
            else:
                waypoints.append({"name": call.group(2), "kind": "waypoint"})

        if not waypoints:
            continue

        name_matches = _WITH_NAME_RE.findall(body)
        title = name_matches[-1] if name_matches else name
        autos[name] = {"title": title, "waypoints": waypoints}

    return autos
