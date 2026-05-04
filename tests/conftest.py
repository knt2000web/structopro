# conftest.py — Configuracion de pytest para StructoPro
# Asegura que la carpeta 'pages' sea accesible al importar funciones puras del modulo.
import sys, os

# Agregar la raiz del proyecto al path para que los tests puedan importar desde pages/
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pages'))

# Stub de streamlit para que las importaciones del modulo no fallen en tests
# (el modulo usa st.* al nivel de modulo, esto lo neutraliza)
import types

_st_stub = types.ModuleType('streamlit')
_st_stub.session_state = {}
_st_stub.cache_data = lambda f=None, **kw: (f if f else lambda fn: fn)
_st_stub.cache_resource = lambda f=None, **kw: (f if f else lambda fn: fn)

def _noop(*a, **kw): return None
def _noop_str(*a, **kw): return ''
def _passthrough(x=None, *a, **kw): return x

for _attr in ['sidebar', 'write', 'error', 'warning', 'info', 'success',
              'title', 'header', 'subheader', 'markdown', 'caption',
              'metric', 'expander', 'tabs', 'columns', 'container',
              'button', 'download_button', 'selectbox', 'radio', 'checkbox',
              'slider', 'number_input', 'text_input', 'text_area',
              'multiselect', 'color_picker', 'file_uploader',
              'image', 'plotly_chart', 'pyplot', 'empty', 'spinner',
              'progress', 'balloons', 'set_page_config', 'stop',
              'data_editor', 'dataframe', 'table', 'divider',
              'experimental_rerun', 'rerun']:
    setattr(_st_stub, _attr, _noop)

# sidebar es un objeto con los mismos metodos
_sidebar = types.SimpleNamespace(**{k: _noop for k in [
    'write', 'error', 'warning', 'info', 'success', 'title', 'header',
    'subheader', 'markdown', 'expander', 'selectbox', 'radio', 'checkbox',
    'slider', 'number_input', 'text_input', 'multiselect', 'button',
    'download_button', 'image', 'divider', 'caption']})
_st_stub.sidebar = _sidebar

sys.modules.setdefault('streamlit', _st_stub)
