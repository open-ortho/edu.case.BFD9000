from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional
from urllib.request import urlopen

from archive.models import Coding, ValueSet, ValueSetConcept


EXPAND_URL = "http://terminology.open-ortho.org/fhir/cwru-ortho-record-types/$expand"
VALUESET_SLUG = "record_types"


def import_record_types(expand_url: str = EXPAND_URL) -> int:
    payload = _fetch_valueset(expand_url)
    valueset = _upsert_valueset(payload)
    codings = _upsert_codings(valueset, payload)
    _sync_valueset_links(valueset, codings)
    return len(codings)


def _fetch_valueset(url: str) -> Dict[str, Any]:
    with urlopen(url) as response:
        raw = response.read().decode("utf-8")
    data: Dict[str, Any] = json.loads(raw)
    return data


def _upsert_valueset(payload: Dict[str, Any]) -> ValueSet:
    compose = payload.get("compose") or {}
    include: List[Dict[str, Any]] = list(compose.get("include") or [])
    code_system_url = None
    if include:
        code_system_url = include[0].get("system")
    expansion = payload.get("expansion") or {}
    contains: List[Dict[str, Any]] = list(expansion.get("contains") or [])
    if contains and not code_system_url:
        code_system_url = contains[0].get("system")

    valueset, created = ValueSet.objects.get_or_create(
        slug=VALUESET_SLUG,
        defaults={
            "url": payload.get("url", ""),
            "name": payload.get("name", VALUESET_SLUG),
            "title": payload.get("title", ""),
            "description": payload.get("description", ""),
            "version": payload.get("version", ""),
            "status": payload.get("status", ""),
            "publisher": payload.get("publisher", ""),
            "code_system_url": code_system_url or "",
        },
    )

    if not created:
        updates: Dict[str, str] = {
            "url": payload.get("url", ""),
            "name": payload.get("name", VALUESET_SLUG),
            "title": payload.get("title", ""),
            "description": payload.get("description", ""),
            "version": payload.get("version", ""),
            "status": payload.get("status", ""),
            "publisher": payload.get("publisher", ""),
            "code_system_url": code_system_url or "",
        }
        changed_fields: List[str] = []
        for field, value in updates.items():
            if getattr(valueset, field) != value:
                setattr(valueset, field, value)
                changed_fields.append(field)
        if changed_fields:
            valueset.save(update_fields=changed_fields)

    return valueset


def _upsert_codings(valueset: ValueSet, payload: Dict[str, Any]) -> List[Coding]:
    expansion = payload.get("expansion") or {}
    contains: Iterable[Dict[str, Any]] = expansion.get("contains") or []
    codings: List[Coding] = []

    for concept in contains:
        system = str(concept.get("system") or "").strip()
        code = str(concept.get("code") or "").strip()
        display = str(concept.get("display") or "").strip()
        definition = str(concept.get("definition") or "").strip()

        if not system or not code:
            continue

        coding, _ = Coding.objects.get_or_create(
            system=system,
            version="",
            code=code,
            defaults={"display": display, "meaning": definition},
        )
        updates: List[str] = []
        if display and coding.display != display:
            coding.display = display
            updates.append("display")
        if definition and coding.meaning != definition:
            coding.meaning = definition
            updates.append("meaning")
        if updates:
            coding.save(update_fields=updates)
        codings.append(coding)

    return codings


def _sync_valueset_links(valueset: ValueSet, codings: List[Coding]) -> None:
    for coding in codings:
        ValueSetConcept.objects.get_or_create(valueset=valueset, coding=coding)

    coding_ids = [coding.id for coding in codings]
    ValueSetConcept.objects.filter(valueset=valueset).exclude(coding_id__in=coding_ids).delete()
