import json
from typer.testing import CliRunner

from shopworld.cli import app
from shopworld.generate.stores import build_simulator_dataset


def test_build_simulator_dataset_is_json_serializable_and_counted():
    dataset = build_simulator_dataset(
        seed=7,
        product_count=2,
        customer_count=3,
        order_count=4,
        location_count=1,
    )

    encoded = json.dumps(dataset)
    decoded = json.loads(encoded)

    assert decoded["manifest"]["seed"] == 7
    assert decoded["manifest"]["record_counts"]["products"] == 2
    assert decoded["manifest"]["record_counts"]["customers"] == 3
    assert decoded["manifest"]["record_counts"]["orders"] == 4
    assert decoded["store"]["products"][0]["created_at"].endswith("+00:00")
    assert isinstance(decoded["store"]["orders"][0]["total_price"], str)


def test_export_simulator_data_command_writes_manifest_and_store(tmp_path):
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "export-simulator-data",
            "--output-dir",
            str(tmp_path),
            "--seed",
            "11",
            "--products",
            "1",
            "--customers",
            "2",
            "--orders",
            "3",
            "--locations",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    store = json.loads((tmp_path / "commerce_store.json").read_text())

    assert manifest["seed"] == 11
    assert manifest["record_counts"]["orders"] == 3
    assert len(store["locations"]) == 1
