"""Reescrita de consulta e serviço de busca.

Módulos: ``types`` (contrato, D-090), ``rewriter`` (``IdentityRewriter``),
``snapshot_loader`` (parquet -> ``Movie``) e ``service`` (``SearchService``).
Os módulos não são importados aqui de propósito: quem só precisa dos tipos
(a interface) não paga o custo de carregar o índice.
"""
