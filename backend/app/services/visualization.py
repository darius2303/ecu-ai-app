import matplotlib.pyplot as plt
import pandas as pd


def generate_fuel_map_heatmap(df: pd.DataFrame, output_path: str):
    plt.figure(figsize=(8, 6))

    heatmap = plt.imshow(df.values, aspect="auto")

    plt.colorbar(heatmap, label="Injection Quantity")

    plt.xticks(range(len(df.columns)), df.columns)
    plt.yticks(range(len(df.index)), df.index)

    plt.xlabel("Boost Pressure")
    plt.ylabel("RPM")

    plt.title("Estimated Stage 1 Fuel Map")

    # 🔥 adăugăm valorile în celule
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            value = df.iloc[i, j]
            plt.text(j, i, f"{value:.1f}", ha="center", va="center", color="white")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()