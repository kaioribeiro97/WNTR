# Create a WaterNetworkModel from an EPANET INP file
import numpy as np
from scipy.stats import lognorm
import networkx as nx
import geopandas as gpd
import matplotlib.pylab as plt
import warnings
import wntr
import folium
from pyproj import Transformer
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.colors as mcolors
import branca.colormap as bcm
from math import sqrt
from wntr.network.elements import Reservoir
from math import sqrt
# Funções:
def vrp(wn, trecho):

    pipe = wn.get_link(trecho)
    start_node = pipe.start_node_name
    end_node = pipe.end_node_name
    wn.remove_link(trecho)

    wn.add_valve(
        name='VRP_' + trecho,
        start_node_name=start_node,
        end_node_name=end_node,
        diameter=pipe.diameter,
        valve_type='PRV',           # Tipo de válvula: PRV para redutora de pressão
        minor_loss= 0.0,             # Ajuste conforme necessário
        initial_setting=20.0,       # Pressão de saída desejada em metros (exemplo)
        initial_status='Active'       # Opened, Closed, Active
    )

def resevatorio(wn, nome_reservatorio, node):    # Nome do reservatório
    base_head = 1156.99 # Carga hidráulica (ajuste conforme sua rede)
    # Supondo que 'wn' é seu WaterNetworkModel e 'nome_no' é o nome do nó desejado
    no = wn.get_node(node)
    coordinates = no.coordinates     # Coordenadas (opcional, ajuste conforme necessário)
    # Parâmetros da tubulação
    nome_tubulacao = 'P_R1_N49'
    comprimento = 0.10               # Comprimento em metros (ajuste conforme necessário)
    diametro = 110                   # Diâmetro em mm (ajuste conforme necessário)
    rugosidade = 140                 # Rugosidade (ajuste conforme necessário)

    # Adiciona o reservatório à rede
    wn.add_reservoir(nome_reservatorio, base_head=base_head, coordinates=coordinates)
    # Adiciona a tubulação conectando o reservatório ao nó N49
    wn.add_pipe(nome_tubulacao, nome_reservatorio, node, length=comprimento, diameter=diametro, roughness=rugosidade)



def dividir_trecho(wn, trecho_original, novo_no, nome_trecho1=None, nome_trecho2=None):
    """
    Divide um trecho (pipe) em dois trechos conectando um novo nó intermediário.
    
    Parâmetros:
        wn: WaterNetworkModel
        trecho_original: str (nome do trecho a ser dividido)
        novo_no: str (nome do nó intermediário)
        nome_trecho1: str (nome do novo trecho 1, opcional)
        nome_trecho2: str (nome do novo trecho 2, opcional)
    """
    # Obtém informações do trecho original
    pipe = wn.get_link(trecho_original)
    start_node = pipe.start_node_name
    end_node = pipe.end_node_name
    diametro = pipe.diameter
    rugosidade = pipe.roughness

    # Calcula os comprimentos com base nas coordenadas
    def distancia(n1, n2):
        c1 = wn.get_node(n1).coordinates
        c2 = wn.get_node(n2).coordinates
        return sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

    comprimento_1 = distancia(start_node, novo_no)
    comprimento_2 = distancia(novo_no, end_node)

    # Define nomes padrão se não fornecidos
    if nome_trecho1 is None:
        nome_trecho1 = trecho_original + "_1"
    if nome_trecho2 is None:
        nome_trecho2 = trecho_original + "_2"

    # Remove o trecho antigo
    wn.remove_link(trecho_original)
    # Adiciona os dois novos trechos
    wn.add_pipe(nome_trecho1, start_node, novo_no, length=comprimento_1, diameter=diametro, roughness=rugosidade)
    wn.add_pipe(nome_trecho2, novo_no, end_node, length=comprimento_2, diameter=diametro, roughness=rugosidade)

    return nome_trecho1, nome_trecho2, comprimento_1, comprimento_2


# Substitua pelos valores reais das coordenadas (x, y) dos nós
coords = {
    'N17': (182325.334803334, 8236241.429658412),
    'N354': (181617.609217913, 8236027.916901818),
    'N351': (181673.985346249, 8236280.518389829)
}

def distancia(p1, p2):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

comprimento_1 = distancia(coords['N17'], coords['N354'])    # ≈ 15,13 m
comprimento_2 = distancia(coords['N354'], coords['N351'])   # ≈ 22,36 m
fator_escala = 188.12067746 / (comprimento_1 + comprimento_2)
comprimento_1_ajustado = comprimento_1 * fator_escala
comprimento_2_ajustado = comprimento_2 * fator_escala
# Suppress warning messages that will be addressed in future WNTR releases
warnings.filterwarnings("ignore", message="Column names longer than 10 characters will be truncated when saved to "
            "ESRI Shapefile.")
warnings.filterwarnings("ignore", message="'crs' was not provided.  The output dataset will not have projection information defined and may not be usable in other systems.")
warnings.filterwarnings("ignore", message="Normalized/laundered field name:")
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS.")
wn = wntr.network.WaterNetworkModel('PK_QD28_TESTE_DOS_NOS_DUPLICADOS (20).inp')
# wn = wntr.network.WaterNetworkModel('gua.inp')
resevatorio(wn, "r1", 'N49')

dividir_trecho(wn, "P375", 'N354')
# Adicione os dois novos trechos
rugosidade = 140
diametro_mm = 32
diametro_m = diametro_mm / 1000.0
wn.add_pipe('P375_1', 'N17', 'N354', length=comprimento_1_ajustado, diameter=diametro_m, roughness=rugosidade)
wn.add_pipe('P375_2', 'N354', 'N351', length=comprimento_2_ajustado, diameter=diametro_m, roughness=rugosidade)

# Adicionar Valvulas
vrp(wn,'P379')
vrp(wn,'P375_1')
vrp(wn,'P366')

sim = wntr.sim.EpanetSimulator(wn)
results = sim.run_sim()

# Extraia pressões do último instante simulado
pressure = results.node['pressure'].iloc[-1]
demanda = results.node['demand'].iloc[-1]
flowrate = results.link['flowrate']
flow_last = flowrate.iloc[-1]
# Substitui valores negativos por zero
pressure = pressure.clip(lower=0)

# Converta as Coordenadas dos Nós para Latitude/Longitude
from pyproj import Transformer

transformer = Transformer.from_crs('EPSG:31983', 'EPSG:4326', always_xy=True)
nodes_latlon = {}
for node in wn.node_name_list:
    x, y = wn.get_node(node).coordinates
    lon, lat = transformer.transform(x, y)
    nodes_latlon[node] = (lat, lon)

# Normaliza as pressões para escala de cores
press_values = list(pressure.values)
# norm = colors.Normalize(vmin=min(press_values), vmax=max(press_values))
# Supondo que press_values já é sua lista de pressões
vmin = min(press_values)
vmax = max(press_values)
# Crie o mapa centralizado em um ponto da rede
lat_centro, lon_centro = list(nodes_latlon.values())[0]
m = folium.Map(location=[lat_centro, lon_centro], zoom_start=15)
velocity = results.link['velocity']


for valve_name in wn.valve_name_list:
    valve = wn.get_link(valve_name)
    start_node = valve.start_node_name
    end_node = valve.end_node_name
    pressao_vrp = pressure[end_node]
    latlon_start = nodes_latlon[start_node]
    latlon_end = nodes_latlon[end_node]
    folium.PolyLine(
        locations=[latlon_start, latlon_end],
        color='black',
        weight=3,
        opacity=0.8,
        popup=f'Válvula {valve_name} - Pressão no nó jusante ({end_node}): {pressao_vrp:.2f} m'
    ).add_to(m)

# Adicionar os trechos de redes
for pipe_name in wn.pipe_name_list:
    pipe = wn.get_link(pipe_name)
    start_node = pipe.start_node_name
    end_node = pipe.end_node_name
    latlon_start = nodes_latlon[start_node]
    latlon_end = nodes_latlon[end_node]
    velocity_last = velocity[pipe_name].iloc[-1]*3.6
    flow_value = flow_last[pipe_name]*1000
    popup_text = f"{pipe_name}: Velocidade = {velocity_last:.2f} m/s - Vazão = {flow_value:.2f} l/s"

    folium.PolyLine(
        locations=[latlon_start, latlon_end],
        color='black',
        weight=3,
        opacity=0.7,
        popup=popup_text
    ).add_to(m)


# Adicione cada nó com cor conforme a pressão

vmin = min(press_values)
vmax = max(press_values)
cmap = plt.colormaps['YlOrBr']
colors = [cmap(i / 10) for i in range(11)]
hex_colors = [mcolors.rgb2hex(c) for c in colors]

colormap = bcm.LinearColormap(hex_colors, vmin=vmin, vmax=vmax, caption='Pressão (m)')
colormap.add_to(m)

# Adiciona um ícone no ponto médio de cada VRP
for valve_name in wn.valve_name_list:
    valve = wn.get_link(valve_name)
    start_node = valve.start_node_name
    end_node = valve.end_node_name
    latlon_start = nodes_latlon[start_node]
    latlon_end = nodes_latlon[end_node]
    # Calcula o ponto médio para posicionar o ícone
    lat_valve = (latlon_start[0] + latlon_end[0]) / 2
    lon_valve = (latlon_start[1] + latlon_end[1]) / 2
    folium.Marker(
        location=[lat_valve, lon_valve],
        popup=f'VRP: {valve_name} ({valve.valve_type})',
        icon=folium.CustomIcon('https://raw.githubusercontent.com/kaioribeiro97/WNTR/f0c8942f2398fb38053519aac3e8560e4f609220/imagens/1.svg',
    icon_size=(40, 40),icon_anchor=(20, 40),
)
    ).add_to(m)


for node, (lat, lon) in nodes_latlon.items():
    press = pressure[node]
    deman = demanda[node]
    color = colormap(press)
    node_obj = wn.get_node(node)
    if isinstance(node_obj, Reservoir):
        folium.Marker(
            location=[lat, lon],
            popup=f'Reservatório {node}: {press:.2f} m - Demanda {deman:.5f} l/s',
            icon=folium.CustomIcon('https://raw.githubusercontent.com/kaioribeiro97/WNTR/f0c8942f2398fb38053519aac3e8560e4f609220/imagens/2.svg',
    icon_size=(40, 40),icon_anchor=(20, 40),)
        ).add_to(m)
    else:
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=f'{node}: {press:.2f} m - Demanda {deman:.5f} l/s'
        ).add_to(m)

m.save('VRP_VAZAMENTO.html')


# Gere o mapa interativo e salve em um arquivo HTML
# wntr.graphics.plot_leaflet_network(wn, filename='rede_mapa.html')