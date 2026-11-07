"""hotfix133 — LOGIC 업로드 검사(_check_pdf)는 거절할 때도 PDF 를 닫는다 (Windows 에서 묶음 폴더가 남던 일)."""
import pymupdf
import pytest
from fastapi import HTTPException

from app.logic import api


def _spy(monkeypatch):
    opened = []
    real = pymupdf.open

    def spy(*a, **k):
        d = real(*a, **k)
        opened.append(d)
        return d
    monkeypatch.setattr(api.pymupdf, "open", spy)
    return opened


def test_rejected_encrypted_pdf_is_closed(tmp_path, monkeypatch):
    src = pymupdf.open()
    src.new_page()
    p = tmp_path / "enc.pdf"
    src.save(p, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")
    opened = _spy(monkeypatch)
    with pytest.raises(HTTPException) as e:
        api._check_pdf(p)
    assert "암호" in e.value.detail
    assert opened and opened[0].is_closed


def test_good_pdf_is_closed(tmp_path, monkeypatch):
    src = pymupdf.open()
    src.new_page()
    p = tmp_path / "ok.pdf"
    src.save(p)
    opened = _spy(monkeypatch)
    api._check_pdf(p)
    assert opened and opened[0].is_closed


def test_not_pdf_rejected(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"not a pdf")
    with pytest.raises(HTTPException):
        api._check_pdf(p)
