import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from epyt import epanet
import operator
import functools
import tempfile
import os
import uuid

st.set_page_config(page_title="EPyT viewer using streamlit",
                   layout="wide")

st.sidebar.title("EPyT - Viewer")
st.sidebar.info(
    """
    The EPANET-Python Toolkit is an open-source software, originally developed by the KIOS Research and 
    Innovation Center of Excellence, University of Cyprus which operates within the Python environment,
    for providing a programming interface for the latest version of EPANET, a hydraulic and quality modeling 
    software created by the US EPA, with Python, a high-level technical computing software. The goal of the 
    EPANET Python Toolkit is to serve as a common programming framework for research and development in the 
    growing field of smart water networks.
    
    EPyT GitHub:  <https://github.com/KIOS-Research/EPyT>
    Web App repository: <https://github.com/Mariosmsk/streamlit-epyt-viewer>
    """
)

# Load default network
option = 'Net1.inp'
d = epanet(option, loadfile=True)

# Find all networks in epyt database.
networksdb = d.getNetworksDatabase()
networksdb.sort()


@st.cache
def save_epanet_file(file_content, inp_name):
    """ Save the uploaded epanet file to a temporary directory"""
    _, file_extension = os.path.splitext(inp_name)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(tempfile.gettempdir(), f"{file_id}{file_extension}")
    with open(file_path, "wb") as file:
        file.write(file_content.getbuffer())
    return file_path


def app():
    title = 'Please select a network from the EPyT database or upload your network.'
    st.markdown(f'<b><p style="color:black;font-size:25px;border-radius:2%;">{title}</p></b>',
                unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        option = st.selectbox("", tuple(networksdb))

    with col2:
        file = st.file_uploader("", type=["inp"])

    if file is not None:
        option = save_epanet_file(file, file.name)
        st.write('You uploaded network:', file.name)

    else:
        st.write('You selected:', option)

    if st.button('RUN'):
        d = epanet(rf'{option}'.replace('\\', '/'), loadfile=True)
        nodecoords = d.getNodeCoordinates()
        x = list(nodecoords['x'].values())
        y = list(nodecoords['y'].values())

        layout = go.Layout(
            autosize=True,
            # width=1000,
            # height=600,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=go.layout.Margin(
                l=5,
                r=5,
                b=5,
                t=5,
                pad=4
            )
        )
        all_figures = []

        node_link_i_ds = d.getNodesConnectingLinksID()
        node_indices = d.getNodeIndex
        for i, l in enumerate(node_link_i_ds):
            x0, y0 = x[node_indices(l[0]) - 1], y[node_indices(l[0]) - 1]
            x1, y1 = x[node_indices(l[1]) - 1], y[node_indices(l[1]) - 1]
            fig1 = px.line(x=[x0, x1], y=[y0, y1])
            all_figures.append(fig1)
        nodes_type = d.getNodeType()
        fig2 = px.scatter(x=x, y=y, color=nodes_type)
        all_figures.append(fig2)
        fig3 = go.Figure(data=functools.reduce(operator.add, [_.data for _ in all_figures]), layout=layout)
        st.plotly_chart(fig3)


try:
    app()
except Exception as e:
    txt = 'Please check your EPANET INP File. Something goes wrong!'
    st.markdown(f'<p style="color:red;font-size:15px;border-radius:2%;">{txt}</p>',
                unsafe_allow_html=True)
