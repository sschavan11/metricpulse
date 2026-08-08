"""
Shared visual system for the app: a validated categorical/status palette,
global CSS, stat-tile cards, and Altair chart theming -- so every page reads
as one system instead of default Streamlit styling.

Palette values and roles follow a standard color-formula method (categorical
hue order assigned by fixed slot, sequential = one hue light->dark, status
colors reserved and never reused for a series, text always in ink tokens,
never the series color).
"""
import altair as alt
import streamlit as st

PAGE_BG = "#f9f9f7"
SURFACE = "#fcfcfb"
PRIMARY_INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED_INK = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"
BORDER = "rgba(11,11,11,0.10)"

# Categorical slots, fixed order -- never cycled, never reassigned by rank.
BLUE = "#2a78d6"    # slot 1: primary metric / treatment
ORANGE = "#eb6834"  # slot 2: control / comparison
AQUA = "#1baf7a"    # slot 3: secondary metric (recovery)

GOOD = "#0ca30c"
CRITICAL = "#d03b3b"

FONT_STACK = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def inject_base_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {PAGE_BG}; }}
        [data-testid="stSidebar"] {{
            background-color: {SURFACE};
            border-right: 1px solid {BORDER};
        }}
        html, body, [class*="css"] {{ font-family: {FONT_STACK}; }}
        h1, h2, h3 {{ color: {PRIMARY_INK}; letter-spacing: -0.01em; }}
        p, li, span {{ color: {SECONDARY_INK}; }}

        .mp-tile {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 16px 18px;
            height: 100%;
        }}
        .mp-tile-label {{
            color: {SECONDARY_INK};
            font-size: 0.78rem;
            font-weight: 500;
            margin-bottom: 6px;
        }}
        .mp-tile-value {{
            color: {PRIMARY_INK};
            font-size: 1.85rem;
            font-weight: 650;
            line-height: 1.1;
        }}
        .mp-tile-delta-good {{ color: {GOOD}; font-size: 0.82rem; font-weight: 600; margin-top: 4px; }}
        .mp-tile-delta-bad {{ color: {CRITICAL}; font-size: 0.82rem; font-weight: 600; margin-top: 4px; }}
        .mp-tile-delta-neutral {{ color: {MUTED_INK}; font-size: 0.82rem; font-weight: 500; margin-top: 4px; }}

        .mp-banner {{
            border-radius: 10px;
            padding: 12px 16px;
            border: 1px solid {BORDER};
            font-size: 0.92rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def stat_tile(label: str, value: str, delta: str | None = None, delta_kind: str = "neutral") -> None:
    """Renders one stat-tile card: label (sentence case, no colon), a bold
    value, and an optional small delta line. delta_kind is 'good' | 'bad' |
    'neutral' (never encoded by color alone elsewhere -- this is a value,
    not a series, so a text color here is fine)."""
    delta_html = ""
    if delta is not None:
        cls = {"good": "mp-tile-delta-good", "bad": "mp-tile-delta-bad"}.get(delta_kind, "mp-tile-delta-neutral")
        delta_html = f'<div class="{cls}">{delta}</div>'
    st.markdown(
        f"""
        <div class="mp-tile">
            <div class="mp-tile-label">{label}</div>
            <div class="mp-tile-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _base_axis(grid: bool) -> alt.Axis:
    return alt.Axis(
        grid=grid,
        gridColor=GRIDLINE,
        domainColor=BASELINE,
        tickColor=BASELINE,
        labelColor=SECONDARY_INK,
        titleColor=SECONDARY_INK,
        labelFontSize=11,
        titleFontSize=12,
    )


def line_chart(df, x: str, y: str, color: str = BLUE, y_title: str | None = None, x_title: str | None = None):
    """A single-series line chart: 2px line, muted axes, hairline gridlines
    on the value axis only, real hover tooltip. No legend -- one color needs
    none; the page's own heading/caption names the series."""
    return (
        alt.Chart(df)
        .mark_line(strokeWidth=2, color=color, interpolate="monotone", clip=True)
        .encode(
            x=alt.X(x, title=x_title, axis=_base_axis(grid=False)),
            y=alt.Y(y, title=y_title, axis=_base_axis(grid=True)),
            tooltip=[alt.Tooltip(x, title=x_title or x), alt.Tooltip(y, title=y_title or y, format=".1f")],
        )
        .properties(height=260, background=SURFACE)
        .configure_view(strokeWidth=0)
    )


def grouped_bar_chart(
    df,
    x: str,
    y: str,
    color_field: str,
    color_domain: list[str],
    color_range: list[str],
    y_title: str | None = None,
):
    """Two-category comparison bar chart. Legend is always shown for 2+
    series -- color-matching alone is never the only identity channel."""
    return (
        alt.Chart(df)
        .mark_bar(size=34, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(x, title=None, axis=_base_axis(grid=False)),
            y=alt.Y(y, title=y_title, axis=_base_axis(grid=True)),
            color=alt.Color(
                color_field,
                scale=alt.Scale(domain=color_domain, range=color_range),
                legend=alt.Legend(title=None, orient="top", labelColor=SECONDARY_INK),
            ),
            tooltip=[alt.Tooltip(x, title=None), alt.Tooltip(y, title=y_title, format=".1f")],
        )
        .properties(height=280, background=SURFACE)
        .configure_view(strokeWidth=0)
    )
