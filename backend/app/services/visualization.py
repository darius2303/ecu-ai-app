import matplotlib.pyplot as plt
import pandas as pd


def generate_fuel_map_heatmap(df: pd.DataFrame, output_path: str):
    plt.figure(figsize=(8, 6))

    heatmap = plt.imshow(df.values, aspect="auto")

    plt.colorbar(heatmap, label="Map Value")

    plt.xticks(range(len(df.columns)), df.columns)
    plt.yticks(range(len(df.index)), df.index)

    plt.xlabel(df.columns.name or "Boost Pressure")
    plt.ylabel(df.index.name or "RPM")

    plt.title("ECU Calibration Map")

    # 🔥 adăugăm valorile în celule
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            value = df.iloc[i, j]
            plt.text(j, i, f"{value:.1f}", ha="center", va="center", color="white")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
