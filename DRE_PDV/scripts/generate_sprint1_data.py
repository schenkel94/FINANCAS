from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Profile:
    name: str
    cogs_range: tuple[float, float]
    tax_range: tuple[float, float]
    commission_range: tuple[float, float]
    returns_range: tuple[float, float]
    fixed_cost_multiplier: tuple[float, float]
    margin_target: tuple[float, float]


def choose_city_region(rng: np.random.Generator) -> tuple[str, str]:
    options = [
        ("Sao Paulo", "Sudeste"),
        ("Rio de Janeiro", "Sudeste"),
        ("Belo Horizonte", "Sudeste"),
        ("Curitiba", "Sul"),
        ("Porto Alegre", "Sul"),
        ("Florianopolis", "Sul"),
        ("Salvador", "Nordeste"),
        ("Recife", "Nordeste"),
        ("Fortaleza", "Nordeste"),
        ("Brasilia", "Centro-Oeste"),
        ("Goiania", "Centro-Oeste"),
        ("Manaus", "Norte"),
        ("Belem", "Norte"),
    ]
    probs = np.array([0.16, 0.1, 0.07, 0.08, 0.07, 0.04, 0.08, 0.07, 0.07, 0.08, 0.05, 0.07, 0.06])
    idx = rng.choice(len(options), p=probs / probs.sum())
    return options[idx]


def make_pdv_base_table(num_pdvs: int, rng: np.random.Generator) -> pd.DataFrame:
    channels = ["Rua", "Shopping", "Franquia", "Quiosque"]
    channel_probs = [0.35, 0.27, 0.24, 0.14]

    records = []
    for i in range(1, num_pdvs + 1):
        city, region = choose_city_region(rng)
        channel = rng.choice(channels, p=channel_probs)

        if channel == "Quiosque":
            metragem = int(rng.normal(28, 6))
        elif channel == "Shopping":
            metragem = int(rng.normal(95, 22))
        elif channel == "Franquia":
            metragem = int(rng.normal(120, 25))
        else:
            metragem = int(rng.normal(85, 18))

        metragem = int(np.clip(metragem, 15, 240))

        opening = pd.Timestamp("2019-01-01") + pd.to_timedelta(int(rng.integers(0, 1980)), unit="D")
        if opening > pd.Timestamp("2024-06-01"):
            opening = pd.Timestamp("2024-06-01")

        records.append(
            {
                "id_pdv": f"PDV{i:03d}",
                "cidade": city,
                "regiao": region,
                "canal": channel,
                "metragem_m2": metragem,
                "data_abertura": opening.date().isoformat(),
            }
        )

    return pd.DataFrame(records)


def generate_data() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(42)

    months = pd.date_range("2024-07-01", "2025-12-01", freq="MS")
    num_pdvs = 70

    pdv_df = make_pdv_base_table(num_pdvs=num_pdvs, rng=rng)

    profiles = {
        "premium_high_margin": Profile(
            name="premium_high_margin",
            cogs_range=(0.40, 0.50),
            tax_range=(0.10, 0.13),
            commission_range=(0.03, 0.06),
            returns_range=(0.01, 0.03),
            fixed_cost_multiplier=(0.95, 1.10),
            margin_target=(0.16, 0.24),
        ),
        "high_revenue_low_margin": Profile(
            name="high_revenue_low_margin",
            cogs_range=(0.60, 0.72),
            tax_range=(0.12, 0.16),
            commission_range=(0.05, 0.09),
            returns_range=(0.04, 0.08),
            fixed_cost_multiplier=(1.00, 1.18),
            margin_target=(0.06, 0.12),
        ),
        "low_revenue_cost_pressure": Profile(
            name="low_revenue_cost_pressure",
            cogs_range=(0.52, 0.64),
            tax_range=(0.10, 0.15),
            commission_range=(0.03, 0.07),
            returns_range=(0.03, 0.07),
            fixed_cost_multiplier=(1.12, 1.35),
            margin_target=(0.04, 0.10),
        ),
        "balanced": Profile(
            name="balanced",
            cogs_range=(0.48, 0.58),
            tax_range=(0.10, 0.14),
            commission_range=(0.03, 0.07),
            returns_range=(0.02, 0.05),
            fixed_cost_multiplier=(0.98, 1.15),
            margin_target=(0.11, 0.18),
        ),
    }

    profile_names = list(profiles.keys())
    profile_probs = np.array([0.18, 0.22, 0.20, 0.40])

    region_mult = {
        "Sudeste": 1.20,
        "Sul": 1.05,
        "Centro-Oeste": 1.00,
        "Nordeste": 0.88,
        "Norte": 0.82,
    }
    channel_mult = {
        "Shopping": 1.25,
        "Rua": 1.00,
        "Franquia": 1.08,
        "Quiosque": 0.58,
    }
    city_rent_index = {
        "Sao Paulo": 1.35,
        "Rio de Janeiro": 1.25,
        "Belo Horizonte": 1.05,
        "Curitiba": 1.02,
        "Porto Alegre": 1.00,
        "Florianopolis": 1.03,
        "Salvador": 0.93,
        "Recife": 0.92,
        "Fortaleza": 0.90,
        "Brasilia": 1.10,
        "Goiania": 0.95,
        "Manaus": 0.90,
        "Belem": 0.86,
    }

    seasonal_factor = {
        1: 0.90,
        2: 0.94,
        3: 0.99,
        4: 1.01,
        5: 1.03,
        6: 1.05,
        7: 1.08,
        8: 1.02,
        9: 1.00,
        10: 1.07,
        11: 1.15,
        12: 1.30,
    }

    sales_rows = []
    var_rows = []
    fixed_rows = []
    target_rows = []

    for _, pdv in pdv_df.iterrows():
        profile_key = rng.choice(profile_names, p=profile_probs)
        profile = profiles[profile_key]

        opening = pd.Timestamp(pdv["data_abertura"])

        base_revenue = rng.uniform(220_000, 760_000)
        base_revenue *= region_mult[pdv["regiao"]]
        base_revenue *= channel_mult[pdv["canal"]]

        if profile_key == "high_revenue_low_margin":
            base_revenue *= rng.uniform(1.20, 1.55)
        elif profile_key == "low_revenue_cost_pressure":
            base_revenue *= rng.uniform(0.68, 0.92)
        elif profile_key == "premium_high_margin":
            base_revenue *= rng.uniform(1.08, 1.28)

        trend = rng.uniform(-0.008, 0.018)

        cogs_pct = rng.uniform(*profile.cogs_range)
        tax_pct = rng.uniform(*profile.tax_range)
        comm_pct = rng.uniform(*profile.commission_range)
        ret_pct = rng.uniform(*profile.returns_range)

        fixed_mult = rng.uniform(*profile.fixed_cost_multiplier)

        aluguel_base = (
            12_000
            + pdv["metragem_m2"] * rng.uniform(140, 280)
            + base_revenue * rng.uniform(0.018, 0.045)
        )
        aluguel_base *= city_rent_index[pdv["cidade"]]
        aluguel_base *= 0.86 if pdv["canal"] == "Quiosque" else 1.0

        folha_base = 22_000 + pdv["metragem_m2"] * rng.uniform(190, 360)
        folha_base += base_revenue * rng.uniform(0.028, 0.055)
        energia_base = 4_000 + pdv["metragem_m2"] * rng.uniform(24, 52)
        tecnologia_base = 2_600 + pdv["metragem_m2"] * rng.uniform(7, 20)

        for idx, month in enumerate(months):
            if month < opening:
                continue

            season = seasonal_factor[month.month]
            macro_noise = rng.normal(1.0, 0.045)
            month_trend = (1 + trend) ** idx
            promo_shock = rng.normal(1.0, 0.035)

            gross_revenue = base_revenue * season * macro_noise * month_trend * promo_shock
            gross_revenue = float(max(gross_revenue, 60_000))

            dynamic_ret_pct = float(np.clip(ret_pct + rng.normal(0, 0.008), 0.005, 0.13))
            devolucoes = gross_revenue * dynamic_ret_pct
            net_revenue = gross_revenue - devolucoes

            cmv = net_revenue * float(np.clip(cogs_pct + rng.normal(0, 0.015), 0.35, 0.78))
            impostos = net_revenue * float(np.clip(tax_pct + rng.normal(0, 0.006), 0.08, 0.19))
            comissoes = net_revenue * float(np.clip(comm_pct + rng.normal(0, 0.007), 0.02, 0.13))

            month_inflation = 1 + 0.0025 * idx
            summer_energy = 1.15 if month.month in {1, 2, 3, 12} else 1.0

            aluguel = aluguel_base * fixed_mult * month_inflation * rng.normal(1.0, 0.025)
            folha = folha_base * fixed_mult * month_inflation * rng.normal(1.0, 0.022)
            energia = energia_base * fixed_mult * month_inflation * summer_energy * rng.normal(1.0, 0.040)
            tecnologia = tecnologia_base * fixed_mult * month_inflation * rng.normal(1.0, 0.020)

            target_revenue = gross_revenue * rng.uniform(1.03, 1.11)
            target_margin = rng.uniform(*profile.margin_target)
            budget_month = (aluguel + folha + energia + tecnologia) * rng.uniform(0.96, 1.06)

            key = {
                "id_pdv": pdv["id_pdv"],
                "mes": month.date().isoformat(),
            }

            sales_rows.append(
                {
                    **key,
                    "receita_bruta": round(gross_revenue, 2),
                    "receita_liquida": round(net_revenue, 2),
                    "devolucoes": round(devolucoes, 2),
                }
            )

            var_rows.append(
                {
                    **key,
                    "cmv": round(cmv, 2),
                    "impostos": round(impostos, 2),
                    "comissoes": round(comissoes, 2),
                }
            )

            fixed_rows.append(
                {
                    **key,
                    "aluguel": round(max(aluguel, 1000), 2),
                    "folha": round(max(folha, 1000), 2),
                    "energia": round(max(energia, 500), 2),
                    "tecnologia": round(max(tecnologia, 500), 2),
                }
            )

            target_rows.append(
                {
                    **key,
                    "meta_receita": round(target_revenue, 2),
                    "meta_margem": round(target_margin, 4),
                    "orcamento_mensal": round(budget_month, 2),
                }
            )

    sales_df = pd.DataFrame(sales_rows)
    var_df = pd.DataFrame(var_rows)
    fixed_df = pd.DataFrame(fixed_rows)
    target_df = pd.DataFrame(target_rows)

    for df in [sales_df, var_df, fixed_df, target_df]:
        df.sort_values(["id_pdv", "mes"], inplace=True)

    return {
        "cadastro_pdvs": pdv_df.sort_values("id_pdv").reset_index(drop=True),
        "vendas_pdv_mensal": sales_df.reset_index(drop=True),
        "custos_variaveis_pdv_mensal": var_df.reset_index(drop=True),
        "custos_fixos_pdv_mensal": fixed_df.reset_index(drop=True),
        "metas_orcamento_pdv_mensal": target_df.reset_index(drop=True),
    }


def validate_outputs(outputs: dict[str, pd.DataFrame]) -> None:
    cadastro = outputs["cadastro_pdvs"]
    vendas = outputs["vendas_pdv_mensal"]
    variaveis = outputs["custos_variaveis_pdv_mensal"]
    fixos = outputs["custos_fixos_pdv_mensal"]
    metas = outputs["metas_orcamento_pdv_mensal"]

    assert cadastro["id_pdv"].is_unique, "id_pdv deve ser unico no cadastro"

    common_keys = ["id_pdv", "mes"]
    v_keys = set(map(tuple, vendas[common_keys].to_records(index=False)))
    for name, df in {
        "custos_variaveis": variaveis,
        "custos_fixos": fixos,
        "metas": metas,
    }.items():
        keys = set(map(tuple, df[common_keys].to_records(index=False)))
        assert keys == v_keys, f"Chaves inconsistentes entre vendas e {name}"

    period = pd.to_datetime(vendas["mes"])
    num_months = period.dt.to_period("M").nunique()
    assert num_months >= 12, "Periodo deve ter pelo menos 12 meses"

    assert (vendas["receita_bruta"] >= vendas["receita_liquida"]).all(), "Receita liquida nao pode exceder bruta"
    assert (vendas["devolucoes"] >= 0).all(), "Devolucoes invalidas"


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    outputs = generate_data()
    validate_outputs(outputs)

    for name, df in outputs.items():
        out_path = data_dir / f"{name}.csv"
        df.to_csv(out_path, index=False, encoding="utf-8")

    print("Arquivos gerados:")
    for path in sorted(data_dir.glob("*.csv")):
        print(f"- {path.name}: {path.stat().st_size} bytes")
