from src.data_loader.parser.xbrl.service import get_four_statements
from .conftest import skip_live

@skip_live
def test_tsla_four_statements_live(sec_user_agent, tmp_path):
    outdir = tmp_path / "tsla"
    frames = get_four_statements(
        ticker="TSLA",
        outdir=str(outdir),
        user_agent=sec_user_agent,
    )
    # Basic smoke checks
    assert set(frames.keys()).issubset({"BS", "IS", "CF", "SE"})
    for k, df in frames.items():
        assert not df.empty
        # Must include label and qname columns
        assert {"label", "qname"}.issubset(df.columns)