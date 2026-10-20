"""Streamlit host for the shared React management UI and isolated public sessions."""

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from sigma_public.react_api.bundle import PublicBundle
from sigma_public.react_api.dispatcher import PublicWorkspace

ROOT = Path(__file__).resolve().parents[1]


@st.cache_resource(show_spinner=False)
def load_bundle(folder, pin):
    bundle = PublicBundle(folder)
    if bundle.pin != pin:
        raise ValueError("Public manifest changed during loading")
    return bundle


def main():
    st.set_page_config(
        page_title="SIGMA · Quản lý nhu cầu & tồn kho",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """<style>[data-testid="stMainBlockContainer"]{padding:0!important;max-width:none!important}[data-testid="stMain"]{padding-top:0}iframe[title*="sigma_react"]{width:100%;border:0}header[data-testid="stHeader"]{height:2rem}</style>""",
        unsafe_allow_html=True,
    )
    folder = ROOT / "release_m3"
    try:
        pin = (folder / "manifest.sha256").read_text().strip()
        bundle = load_bundle(str(folder), pin)
        if "sigma_react_workspace" not in st.session_state:
            st.session_state.sigma_react_workspace = PublicWorkspace(bundle)
        workspace = st.session_state.sigma_react_workspace
        if workspace.bundle.pin != pin:
            st.session_state.sigma_react_workspace = PublicWorkspace(bundle)
            workspace = st.session_state.sigma_react_workspace
            st.session_state.pop("sigma_react_responses", None)
        responses = st.session_state.setdefault("sigma_react_responses", {})
        command = st.session_state.get("sigma_react_ui") or {}
        requests = command.get("requests", []) if isinstance(command, dict) else []
        if not isinstance(requests, list) or len(requests) > 32:
            raise ValueError("Unexpected component request batch")
        for request in requests:
            if not isinstance(request, dict):
                raise ValueError("Unexpected component request")
            ident = request.get("id")
            if not isinstance(ident, str) or len(ident) > 80:
                raise ValueError("Unexpected request key")
            if ident not in responses:
                responses[ident] = workspace.call(
                    request.get("path"),
                    request.get("method", "GET"),
                    request.get("body"),
                    request.get("idempotency"),
                )
        while len(responses) > 96:
            responses.pop(next(iter(responses)))
        component = components.declare_component(
            "sigma_react", path=str(ROOT / "react_ui")
        )
        component(
            responses={r["id"]: responses[r["id"]] for r in requests},
            frame_height=900,
            release_version=bundle.meta["version"],
            key="sigma_react_ui",
            default={},
        )
    except (ValueError, OSError, KeyError) as error:
        st.error("Không thể tải bản SIGMA đã kiểm chứng. " + str(error)[:180])
