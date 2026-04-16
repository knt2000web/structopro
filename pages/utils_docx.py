import io

def fig_to_docx_white(fig):
    """
    Convierte cualquier figura Matplotlib (modo oscuro de Streamlit) a modo claro
    para exportación a DOCX/PDF. Garantiza fondo blanco opaco y elimina el canal
    alfa que genera manchas negras en visores de Word/PDF. Restaura el modo oscuro
    al finalizar para que la UI de Streamlit no se vea afectada.
    """
    # Guardar estado original de la figura
    orig_fig_facecolor = fig.get_facecolor()

    # Forzar fondo blanco y opaco (eliminar canal alfa)
    fig.patch.set_facecolor('white')
    fig.patch.set_alpha(1.0)

    orig_axes_props = []
    for ax in fig.get_axes():
        orig_axes_props.append({
            'facecolor':    ax.get_facecolor(),
            'title_color':  ax.title.get_color(),
            'xaxis_color':  ax.xaxis.label.get_color(),
            'yaxis_color':  ax.yaxis.label.get_color(),
            'spines_colors': {k: v.get_edgecolor() for k, v in ax.spines.items()},
        })

        # Fondo claro y opaco en los ejes
        ax.set_facecolor('#ffffff')
        ax.patch.set_alpha(1.0)

        # Textos y bordes oscuros para impresión
        ax.title.set_color('#1a1a1a')
        ax.xaxis.label.set_color('#1a1a1a')
        ax.yaxis.label.set_color('#1a1a1a')
        ax.tick_params(colors='#1a1a1a')
        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')

        # Ejes 3D: forzar paneles blancos si existen
        try:
            ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
            ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
            ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 1.0))
        except AttributeError:
            pass  # No es un eje 3D

    # Capturar en buffer PNG sin transparencia
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=200, facecolor='white', transparent=False,
                bbox_inches='tight')
    buf.seek(0)

    # Restaurar modo oscuro para la UI de Streamlit
    fig.patch.set_facecolor(orig_fig_facecolor)
    for i, ax in enumerate(fig.get_axes()):
        props = orig_axes_props[i]
        ax.set_facecolor(props['facecolor'])
        ax.title.set_color(props['title_color'])
        ax.xaxis.label.set_color(props['xaxis_color'])
        ax.yaxis.label.set_color(props['yaxis_color'])
        for k, spine in ax.spines.items():
            spine.set_edgecolor(props['spines_colors'][k])

    return buf
