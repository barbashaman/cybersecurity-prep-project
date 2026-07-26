"""Advisory generator.

Advisories are generated, never hand-written. This renders a markdown advisory
under ``documentation/advisories/`` from a Jinja2 template fed by the failing
test's structured result plus scanner evidence (ZAP alert id, Bandit test id,
Semgrep rule id).

Every generated document carries the mandated header:

    Document Name: ...
    Covered Elements: ...
    Creation Date: dd/MM/yyyy-HH:mm:ss.fff
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

MANDATED_DATE_FORMAT = "%d/%m/%Y-%H:%M:%S.%f"


@dataclass(frozen=True, slots=True)
class ScannerEvidence:
    """A single piece of tool evidence backing the advisory."""

    tool: str
    identifier: str
    description: str


@dataclass(frozen=True, slots=True)
class AdvisoryInput:
    """Structured input for one advisory, assembled from a detection run."""

    document_name: str
    covered_elements: str
    iteration: str
    owasp_risk: str
    owasp_api_cross_reference: str
    summary: str
    failing_test: str
    evidence: list[ScannerEvidence] = field(default_factory=list)
    remediation_summary: str = ""

    def creation_timestamp(self) -> str:
        """The mandated ``dd/MM/yyyy-HH:mm:ss.fff`` timestamp (millisecond precision)."""
        stamp = datetime.now().strftime(MANDATED_DATE_FORMAT)
        # strftime gives microseconds (6 digits); the convention wants milliseconds (3).
        return stamp[:-3]


class AdvisoryGenerator:
    """Renders :class:`AdvisoryInput` into a markdown advisory file."""

    def __init__(
        self,
        template_dir: Path,
        template_name: str = "advisory_template.md.j2",
    ) -> None:
        self._environment = Environment(
            loader=FileSystemLoader(str(template_dir)),
            undefined=StrictUndefined,
            # Output is markdown, not HTML; autoescaping would corrupt tables/code fences.
            autoescape=False,  # noqa: S701
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        self._template_name = template_name

    def render(self, advisory: AdvisoryInput) -> str:
        template = self._environment.get_template(self._template_name)
        return template.render(
            advisory=advisory,
            creation_date=advisory.creation_timestamp(),
        )

    def write(self, advisory: AdvisoryInput, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = advisory.document_name.lower().replace(" ", "-")
        target = output_dir / f"{advisory.iteration}-{slug}.md"
        target.write_text(self.render(advisory), encoding="utf-8")
        return target
