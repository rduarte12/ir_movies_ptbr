"""Preprocessador: minúsculas, acentos, tokenização, stopwords, stemming."""

import re
from dataclasses import dataclass, field

import nltk
from nltk.stem import SnowballStemmer
from unidecode import unidecode


@dataclass
class PreprocessTrace:
    """Rastreio completo do pré-processamento, usado na explicabilidade (nível 3)."""

    original_tokens: list[str]
    stopped: list[str]
    stems: list[str]
    stem_to_surface: dict[str, list[str]] = field(default_factory=dict)


class Preprocessor:
    """Pipeline de pré-processamento PT-BR conforme D-014.

    Etapas: minúsculas → remoção de acentos → tokenização regex → stopwords → stemming.
    """

    def __init__(self, cfg: dict) -> None:
        nltk.download("stopwords", quiet=True)
        self._stemmer = SnowballStemmer("portuguese")
        self._strip_accents = cfg.get("strip_accents", True)

        from nltk.corpus import stopwords

        raw_stops = set(stopwords.words("portuguese"))
        raw_stops |= set(cfg.get("extra_stopwords", []))
        self._stopwords = {unidecode(w.lower()) for w in raw_stops}

    def _normalize(self, text: str) -> str:
        result = text.lower()
        if self._strip_accents:
            result = unidecode(result)
        return result

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", self._normalize(text))

    def tokens(self, text: str) -> list[str]:
        toks = self._tokenize(text)
        return [self._stemmer.stem(t) for t in toks if t not in self._stopwords]

    def trace(self, text: str) -> PreprocessTrace:
        original_tokens = self._tokenize(text)
        stopped: list[str] = []
        kept: list[str] = []
        for t in original_tokens:
            if t in self._stopwords:
                stopped.append(t)
            else:
                kept.append(t)

        stems: list[str] = []
        stem_to_surface: dict[str, list[str]] = {}
        for t in kept:
            s = self._stemmer.stem(t)
            stems.append(s)
            if s not in stem_to_surface:
                stem_to_surface[s] = []
            if t not in stem_to_surface[s]:
                stem_to_surface[s].append(t)

        return PreprocessTrace(
            original_tokens=original_tokens,
            stopped=stopped,
            stems=stems,
            stem_to_surface=stem_to_surface,
        )
