---
title: DRE PDV Analytics
emoji: 📊
colorFrom: blue
colorTo: cyan
sdk: docker
pinned: false
license: mit
short_description: Demonstrativo de Resultados por Ponto de Venda
---

# DRE PDV Analytics 📊

Dashboard interativo de Demonstrativo de Resultados (DRE) por Ponto de Venda, construído com **Plotly Dash**.

## Funcionalidades

- KPIs consolidados (Receita Líquida, EBITDA, Lucro Líquido, Margem Operacional)
- DRE completo com visão sidebar
- Gráficos interativos: donut por canal, scatter receita × margem, evolução temporal, top PDVs
- Mapa do Brasil por região
- Tabela de PDVs críticos com planos de ação
- Filtros por período, região, canal e PDV

## Stack

- [Plotly Dash](https://dash.plotly.com/)
- [Pandas](https://pandas.pydata.org/) + [NumPy](https://numpy.org/)
- [Gunicorn](https://gunicorn.org/)
- Deploy via Docker no Hugging Face Spaces

## Autor

**Mário Schenkel** · [Portfolio](https://schenkel94.github.io/portfolio/)
