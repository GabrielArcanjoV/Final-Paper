import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from datetime import datetime
from dateutil import tz
import time

import os 

# IDENTIFIES THE TIME ZONE
from_zone = tz.tzutc()
to_zone = tz.tzlocal()


# IDENTIFIES THE FOLDER THE CODE IS IN 
caminho = os.getcwd()

#'start_time = time.perf_time()

# LISTS ALL THE TXT FILES IN THE FOLDER + '/dados' TO BE READ 
# NOTE: YOU HAVE PUT ALL THE TXT FILES YOU WANT TO READ IN A FOLDER
# CALLED 'dados'

file_list = sorted(os.listdir(caminho + "/dados"))

# FIRST WE SAVE EACH EVENT TO A TEMPORARY VECTOR F, AND VERIFY IF IT IS CORRUPTED OR BROKEN
# IF THE EVENT IS CORRUUPTED OR BROKE IT IS REMOVED
# IF THE EVENT IS OK, IT IS SAVED IN THE 'dados' PANDAS DATAFRAME

for filename in file_list:
    with open(os.path.join(caminho + "/dados", filename), 'r') as file:
      pontos = 0
      i = 0
      j = 0
      broken_points = 0                                                             # contador de espaços
      broken_values = 0                                                             # contador de erros de faixa
      eventos_descartados = 0
      F = [] 
      Fi = []
      dados = pd.DataFrame()
      for line in file:
        lista = line.split('\n')
        if '\x00' in line:                                                          # valor corrompido -> broken_points++
          broken_points = broken_points + 1 
        if '\x00' not in line and ',' not in line and isinstance(lista[0], int):
          if int(lista[0]) < 50 or int(lista[0]) > 3999:                            # verifica erro de faixa
            broken_values = broken_values + 1
        if ',' in line:                                                             # encontra a timestamp
          timestamp = line.strip()
          if pontos == 4000 and broken_points == 0 and broken_values == 0 :         # verifica a janela e valores corrompidos
            for j in F:
              Fi.append(int(j))
            for t in timestamp.split(','):
              Fi.append(t)
            dados = pd.concat([dados, pd.DataFrame([Fi])], ignore_index=True)       # monta o DataFrame 'dados'
          else:                                                                     # incorreta -> apaga o evento
            eventos_descartados = eventos_descartados + 1
          pontos = 0
          i = 0
          j = 0
          broken_points = 0
          broken_values = 0
          F = []
          Fi = []
          timestamp = []
          t = 0
        else:                                                                       # salva os pontos em F
          pontos = pontos + 1
          F.append(lista[0])
      #print(eventos_descartados)
    
    #tempo_1 = time.perf_time() - start_time
    
#======================================================================================
# HERE WE FILTER ALL THE DATA USING A HIGH PASS FILTER TO REMOVE THE DC COMPONENT (40Hz)
# OF EACH EVENT, SO WE CAN LATER CUT EACH EVENT TO A TIME WINDOW 
# THE EVENTS AS SAVED INTO A PANDAS DATAFRAME CALLED 'dados_filtrados'

    from scipy.signal import filtfilt
    from scipy import stats
    import matplotlib.pyplot as plt
    from scipy.signal import butter
    from scipy import signal
    import scipy
    
    def butter_highpass(cutoff, fs, order):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = signal.butter(order, normal_cutoff, btype='high', analog=False)
        return b, a
    
    def butter_highpass_filter(data, cutoff, fs, order):                            # definição da função de filtro
        b, a = butter_highpass(cutoff, fs, order=order)
        y = signal.filtfilt(b, a, data)
        return y
    
    cutoff = 40                                                                     # frequência de corte
    fs =1000000                                                                     # taxa de amostragem
    order = 1                                                                       # ordem do filtro
    
    k = 0
    dados_filtrados = pd.DataFrame()
    t = 0
    
    for k in range(0, len(dados)):
      evento_filtrado = butter_highpass_filter(dados.iloc[k, 0:4000],     
                                               cutoff, fs, order)                   # aplica o filtro DC
      evento_filtrado = pd.DataFrame([evento_filtrado])                                        
      timestamp_evento_filtrado = dados.iloc[k, 4000:4008]                          # busca a timestamp do evento
      timestamp_evento_filtrado = pd.DataFrame([timestamp_evento_filtrado])
      k = k + 1
      evento_filtrado = pd.concat([evento_filtrado.reset_index(drop=True), 
                                   timestamp_evento_filtrado.reset_index(drop=True)], 
                                  ignore_index=True, axis=1)                        # junta evento filtrado e timestamp                                  
      dados_filtrados = pd.concat([dados_filtrados, evento_filtrado], 
                                  ignore_index=True)                                # monta o DataFrame 'dados_filtrados'
      evento_filtrado = []
      timestamp_evento_filtrado = []
    
    k = 0
    t = 0
    
    #tempo_2 = time.perf_time() - start_time - tempo_1
    
#==========================================================================
# NOW WE CUT EACH EVENT TO A 1100 MICROSECONDS TIME WINDOW 
# THE DETAILS OF HOW THIS WORKS CAN BE FOUND AT ..........
# THE FINAL EVENTS ARE SAVED TO A PANDAS DATAFRAME CALLED 'dados_cortados_filtrados'

    k = 0
    l = 0
    G = []
    timestamp_cortado = []
    dt = 2                                                                          # intervalos futuros
    intervalo = 8                                                                   # -8 +8
    Diff = []
    evento_cort_refilt = []
    dados_cortados_filtrados = pd.DataFrame()
    dados_nao_cortados_filtrados_salvos = pd.DataFrame()
    eventos_descartados_2 = 0
    indexador = 0 
    evento_nao_cortado_salvo = []
    
    for k in range(0, len(dados_filtrados)):
      G = dados_filtrados.iloc[k, 0:4000]                                           # separa o evento da timestamp
      timestamp_cortado = dados_filtrados.iloc[k, 4000:4008]                        # busca a timestamp do evento
      k = k + 1                               
      for l in range(0, 4000 - dt):
        dy_dt = abs(G[l] - G[l+2])                                                  # calcula a diferença entre a amostra presente e a amostra futura
        Diff.append(dy_dt)
        l = l + 1
      max_diff = max(Diff)
      max_diff_index = Diff.index(max_diff)                                         # encontra o index da máxima diferença
      if max_diff_index >= intervalo and max_diff_index <= 4000 - intervalo:        # verifica se há 8 valores antes e 8 valores depois
        max_value = max(G[max_diff_index - intervalo:max_diff_index + intervalo])   # encontra o valor de pico max
        H = G.tolist()
        max_value_index = H.index(max_value)
        min_value = min(G[max_diff_index - intervalo:max_diff_index + intervalo])   # encontra o valor de pico min
        min_value_index = H.index(min_value)
        if abs(max_value) > abs(min_value):                                         # verifica quem é o pico baseado na magnitude
          peak_index = max_value_index
          #indicador = 'positivo'
        elif abs(max_value) < abs(min_value):
          peak_index = min_value_index
          #indicador = 'negativo'
        else:
          peak_index = max_value_index
          #indicador = 'igual'
        if peak_index > 100 and peak_index < 3000:                                  # verifica se há 99 pontos antes e 1000 pontos depois do pico
          evento_cortado = G[peak_index - 100:peak_index + 1000]                    # corta o evento em 1100 pontos
          evento_nao_cortado_salvo = G
          '''media_30 = np.median(evento_cortado[0:30])                             # calcula a média dos 30 primeiros pontos
          for valor in evento_cortado:                                              # subtrai os pontos da média
           valor_novo = valor - media_30
           evento_cort_refilt.append(valor_novo)'''
          #plt.plot(range(0,1100),evento_cortado)
          timestamp_cortado = pd.DataFrame([timestamp_cortado])
          
          evento_cortado = pd.DataFrame([evento_cortado])
          evento_nao_cortado_salvo = pd.DataFrame([evento_nao_cortado_salvo])
          
          evento_cortado = pd.concat([evento_cortado.reset_index(drop=True),
                                      timestamp_cortado.reset_index(drop=True)],
                                      ignore_index=True, axis=1)                    # junta o evento cortado e filtrado com a timestamp 
          
          evento_nao_cortado_salvo = pd.concat([evento_nao_cortado_salvo.reset_index(drop=True),
                                      timestamp_cortado.reset_index(drop=True)],
                                      ignore_index=True, axis=1)
          
          dados_cortados_filtrados = pd.concat([dados_cortados_filtrados, 
                                                evento_cortado],         
                                                ignore_index=True)                  # monta o DataFrame 'dados_cortados_filtrados'  
          
          dados_nao_cortados_filtrados_salvos = pd.concat([dados_nao_cortados_filtrados_salvos, 
                                                evento_nao_cortado_salvo],         
                                                ignore_index=True)
        else:
          eventos_descartados_2 = eventos_descartados_2 + 1
          indexador = indexador + 1
        timestamp_cortado = []
        evento_cortado = []
      else:
        eventos_descartados_2 = eventos_descartados_2 + 1
        indexador = indexador + 1
      
      l = 0
      G = []
      H = []
      Diff = []
      evento_cortado = []
      timestamp_cortado = [] 
    k = 0
    
# HERE EACH EVENT IS PLOTTED 
# YOU HAVE CREATE A NEW FOLDER CALLED 'plots' IN THE SAME FOLDER THE CODE IS RUNNING AT

    #tempo_3 = time.perf_time() - start_time - tempo_1 - tempo_2
    plt.rcParams["figure.figsize"] = (10,8)
    
    try:
        new_dir = filename[:-4]
        parent_dir = caminho + "/plots/"
    
        path = os.path.join(parent_dir, new_dir).replace('\\', '/')
        
        os.mkdir(path)
        
        print(f'Directory {new_dir} created')
        
    except:
        print(f'directory {new_dir} already exists')
        
        
    for i in range(0, dados_cortados_filtrados.shape[0]):
        
    
        timestamp_utc = []
        #print(dados_cortados_filtrados.iloc[i, 1100:1107])
        for i3 in dados_cortados_filtrados.iloc[i, 1100:1107]:
            timestamp_utc.append(i3)
        timestamp_utc_str = f'{timestamp_utc[0]},{timestamp_utc[1]},{timestamp_utc[2]},{timestamp_utc[3]},{timestamp_utc[4]},{timestamp_utc[5]}'
        string_utc = f'{timestamp_utc[0]}/{timestamp_utc[1]}/{timestamp_utc[2]} {timestamp_utc[3]}:{timestamp_utc[4]}:{timestamp_utc[5]:{timestamp_utc[6]}}'
        #print(timestamp_utc_str)
        utc = datetime.strptime(timestamp_utc_str, '%d,%m,%Y,%H,%M,%S')
        utc = utc.replace(tzinfo=from_zone)
        central = utc.astimezone(to_zone)
        stamp = str(central).split(':')
        string = f'{stamp[0]}:{stamp[1]}:{stamp[2]}'
        string = string[:-3]
        
        #fig = plt.plot(range(0, 1100), dados_cortados_filtrados.iloc[i,0:1100])
        
        
        fig, (ax1, ax2) = plt.subplots(2)
        
        # HERE YOU CAN USE {string} TO PLOT THE TITLE WITH LOCAL TIME 
        # OR YOU CAN USE {string_utc} TO PLOT USING UTC TIME 
        fig.suptitle(f'Local: Unicamp \n Data: {string}')
        
        
        ax1.plot(range(0, 4000), dados_nao_cortados_filtrados_salvos.iloc[i,0:4000])
        ax2.plot(range(0, 1100), dados_cortados_filtrados.iloc[i,0:1100])

        #plt.title(f'Local: Unicamp \n Data: {string}') ----  NOT BEING USED ANYMORE
        string = string.replace(' ', '_').replace(':', '_').replace('-', '_') + '.png'
        
        
        #plt.savefig(os.path.join(path, string).replace('\\', '/'))
        plt.savefig(path + '/' + string)
        plt.show()
    
    

