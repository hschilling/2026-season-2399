"""Resolve Java ``Pose2d`` expressions from FieldConstants.java into
plain ``(x_meters, y_meters, theta_degrees)`` tuples.

This is deliberately a focused parser for the expression forms that actually
appear in this repo's ``FieldConstants`` file, not a general Java evaluator.
"""

import ast
import math
import re

INCHES_TO_METERS = 0.0254

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_POSE_DECL_RE = re.compile(r"public\s+static\s+final\s+Pose\s+(\w+)\s*=")


def strip_java_comments(source):
    """Remove ``/* */`` and ``//`` comments so commented-out code is ignored."""
    source = _BLOCK_COMMENT_RE.sub("", source)
    source = _LINE_COMMENT_RE.sub("", source)
    return source


def _extract_balanced(text, open_idx):
    """Return the substring from ``text[open_idx]`` (a '(') to its matching ')'."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx : i + 1]
    raise ValueError("unbalanced parentheses starting at %d" % open_idx)


def extract_named_poses(source):
    """Return ``{NAME: (x_m, y_m, theta_deg)}`` for every ``Pose`` constant.

    Parses ``public static final Pose NAME = new Pose("label", new Pose2d(...))``
    declarations. Constants whose Pose2d expression cannot be resolved are skipped.
    """
    source = strip_java_comments(source)
    result = {}
    for match in _POSE_DECL_RE.finditer(source):
        name = match.group(1)
        semi = source.find(";", match.end())
        segment = source[match.end() : semi if semi != -1 else len(source)]
        idx = segment.find("new Pose2d")
        if idx == -1:
            continue
        open_idx = segment.find("(", idx)
        pose2d_expr = "new Pose2d" + _extract_balanced(segment, open_idx)
        pose2d_expr = re.sub(r"\s+", " ", pose2d_expr).strip()
        try:
            result[name] = parse_pose2d(pose2d_expr)
        except (ValueError, AssertionError):
            continue
    return result


_DISTANCE_DECL_RE = re.compile(r"public\s+static\s+final\s+Distance\s+(\w+)\s*=")
_POSE2D_DECL_RE = re.compile(r"public\s+static\s+final\s+Pose2d\s+(\w+)\s*=")


def _rhs(source, after_idx):
    """Return the whitespace-normalized text between ``after_idx`` and the next ';'."""
    semi = source.find(";", after_idx)
    end = semi if semi != -1 else len(source)
    return re.sub(r"\s+", " ", source[after_idx:end]).strip()


def _parse_distance_constants(source):
    """Return ``{NAME: meters}`` for ``public static final Distance`` constants."""
    symbols = {}
    for match in _DISTANCE_DECL_RE.finditer(source):
        name = match.group(1)
        try:
            symbols[name] = parse_length(_rhs(source, match.end()), symbols)
        except (ValueError, SyntaxError):
            continue
    return symbols


def _apply_transform(base, dx, dy, drot_deg):
    """Apply a ``Transform2d`` to a base ``(x, y, deg)`` pose (WPILib semantics)."""
    bx, by, bdeg = base
    theta = math.radians(bdeg)
    nx = bx + dx * math.cos(theta) - dy * math.sin(theta)
    ny = by + dx * math.sin(theta) + dy * math.cos(theta)
    return (nx, ny, bdeg + drot_deg)


def resolve_all_poses(field_constants_source):
    """Resolve every usable pose constant in FieldConstants.java.

    Merges the ``Pose`` record constants with top-level ``Pose2d`` constants,
    including derived ones built via ``base.plus(new Transform2d(...))``.
    Returns ``{NAME: (x_m, y_m, theta_deg)}``.
    """
    source = strip_java_comments(field_constants_source)
    symbols = _parse_distance_constants(source)
    poses = extract_named_poses(source)

    pending = [(m.group(1), _rhs(source, m.end())) for m in _POSE2D_DECL_RE.finditer(source)]
    # Resolve iteratively so constants defined in terms of earlier ones settle.
    progress = True
    while pending and progress:
        progress = False
        still_pending = []
        for name, rhs in pending:
            value = _resolve_pose2d_rhs(rhs, poses, symbols)
            if value is None:
                still_pending.append((name, rhs))
            else:
                poses[name] = value
                progress = True
        pending = still_pending

    return poses


def _resolve_pose2d_rhs(rhs, poses, symbols):
    """Resolve a top-level Pose2d RHS, or return None if dependencies are unmet."""
    plus_idx = rhs.find(".plus(")
    if plus_idx != -1:
        base_name = rhs[:plus_idx].strip()
        if base_name not in poses:
            return None
        open_idx = rhs.find("(", plus_idx)
        transform_call = _extract_balanced(rhs, open_idx)[1:-1].strip()
        dx, dy, drot = _split_top_level_commas(_unwrap(transform_call, "new Transform2d"))
        return _apply_transform(
            poses[base_name],
            parse_length(dx, symbols),
            parse_length(dy, symbols),
            parse_rotation(drot),
        )
    if rhs.startswith("new Pose2d"):
        try:
            return parse_pose2d(rhs)
        except (ValueError, AssertionError):
            return None
    return None


def _safe_eval_number(expr):
    """Evaluate a pure-arithmetic numeric expression like ``47.0 / 2.0``.

    Only numeric literals and +, -, *, / (and unary +/-) are allowed.
    """
    node = ast.parse(expr.strip(), mode="eval")

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp):
            left, right = _eval(n.left), _eval(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            if isinstance(n.op, ast.Div):
                return left / right
        if isinstance(n, ast.UnaryOp):
            operand = _eval(n.operand)
            if isinstance(n.op, ast.UAdd):
                return operand
            if isinstance(n.op, ast.USub):
                return -operand
        raise ValueError("unsupported numeric expression: %r" % expr)

    return _eval(node)


def _split_top_level_commas(inner):
    """Split a comma-separated argument list, ignoring commas inside parentheses."""
    parts = []
    depth = 0
    current = []
    for ch in inner:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return parts


def _unwrap(expr, prefix):
    """Return the inner text of ``prefix( ... )`` for a stripped expression."""
    expr = expr.strip()
    assert expr.startswith(prefix + "(") and expr.endswith(")"), expr
    return expr[len(prefix) + 1 : -1]


def parse_pose2d(expr):
    """Return ``(x_m, y_m, theta_deg)`` from a Java ``new Pose2d(...)`` expression.

    Supports the ``new Pose2d(new Translation2d(...), <rotation>)`` form and the
    raw ``new Pose2d(x, y, <rotation>)`` form.
    """
    inner = _unwrap(expr, "new Pose2d")
    args = _split_top_level_commas(inner)

    if len(args) == 2 and args[0].startswith("new Translation2d"):
        tx, ty = _split_top_level_commas(_unwrap(args[0], "new Translation2d"))
        return parse_length(tx), parse_length(ty), parse_rotation(args[1])

    if len(args) == 3:
        return parse_length(args[0]), parse_length(args[1]), parse_rotation(args[2])

    raise ValueError("unsupported Pose2d expression: %r" % expr)


# Named Rotation2d constants used in this repo, in degrees.
_ROTATION_CONSTANTS = {
    "Rotation2d.kZero": 0.0,
    "Rotation2d.k180deg": 180.0,
    "Rotation2d.kCCW_90deg": 90.0,
    "Rotation2d.kCW_90deg": -90.0,
    "Rotation2d.kPi": 180.0,
}


def parse_rotation(expr):
    """Return a heading in degrees from a Java Rotation2d expression.

    Handles named constants (``Rotation2d.kZero`` etc.), ``Rotation2d.fromDegrees(n)``,
    and ``new Rotation2d(Degrees.of(n))``.
    """
    expr = expr.strip()
    if expr in _ROTATION_CONSTANTS:
        return _ROTATION_CONSTANTS[expr]
    if expr.startswith("Rotation2d.fromDegrees(") and expr.endswith(")"):
        return _safe_eval_number(expr[len("Rotation2d.fromDegrees(") : -1])
    if expr.startswith("new Rotation2d(Degrees.of(") and expr.endswith("))"):
        return _safe_eval_number(expr[len("new Rotation2d(Degrees.of(") : -2])
    raise ValueError("unsupported rotation expression: %r" % expr)


def parse_length(expr, symbols=None):
    """Return a length in meters from a Java length expression.

    Handles ``Meters.of(...)``, ``Inches.of(...)`` (converted), and a bare
    numeric literal/expression (treated as meters, matching ``new Pose2d(x, y, ...)``).
    When ``symbols`` (a ``name -> meters`` map of named ``Distance`` constants) is
    given, also resolves bare identifiers and ``IDENT.unaryMinus()``.
    """
    expr = expr.strip()
    if expr.startswith("Meters.of(") and expr.endswith(")"):
        return _safe_eval_number(expr[len("Meters.of(") : -1])
    if expr.startswith("Inches.of(") and expr.endswith(")"):
        return _safe_eval_number(expr[len("Inches.of(") : -1]) * INCHES_TO_METERS
    if symbols is not None:
        if expr.endswith(".unaryMinus()"):
            return -parse_length(expr[: -len(".unaryMinus()")], symbols)
        if expr in symbols:
            return symbols[expr]
    return _safe_eval_number(expr)
