import datetime
from time import sleep
import PySimpleGUI as sg
from threading import Timer
import os
import dados_db
import subprocess

#id, nome, ultima, proxima, estado, tarefa,
# meses, dias, horas, minutos, repetir, especificos, diretorio
class Trabalho:
    def __init__(self, registro:tuple) -> None:
        self.id = registro[0]
        self.nome = registro[1]
        self.meses = registro[6].split(',')
        
        #verifica se existe [dias especificos] configurados
        #essa opção tem precedência sobre [dias da semana]
        self.diasE = None
        if len(registro[11]) > 0:
            self.diasE = registro[11].split(',')
        
        self.dias = registro[7].split(',')
        self.horas = registro[8].split(',')
        self.minutos = registro[9]
        self.repete = registro[10]
        self.base = None
        self.habilitada = registro[4]

        self.comando = registro[5]
        self.diretorio = registro[12]
        self.escondido = 0

        if self.habilitada:
            self.data_base()

    def data_base(self):
        if not self.habilitada:
            return

        #obtem a data atual
        d1 = datetime.datetime.now()
        flag = -1

        #Lista que deverá ser preenchida a data da tarefa
        dt=[d1.year, flag, flag, flag, flag, d1.second]

        #----------------monta a data base--------------------
        if str(d1.month) in self.meses: dt[1] = d1.month
        
        if self.diasE != None:  #dias especificos
            if str(d1.day) in self.diasE: dt[2] = d1.day
        else:   #dias da semana
            if str(d1.weekday()) in self.dias: dt[2] = d1.day

        if str(d1.hour) in self.horas: dt[3] = d1.hour
        dt[4] = self.minutos
        #-----------------------------------------------------

        #verifica se todos os campos foram preenchidos
        if flag in dt:
            self.base = None
            return
        
        #se a data base for menor que a data atual, faz um loop até
        #encontrar o proximo horário válido com base no valor informado em [repete]
        d2 = datetime.datetime(dt[0],dt[1],dt[2],dt[3],dt[4],dt[5])
        if (d2 < d1) and self.repete > 0:
            while d2 <= d1:
                d2 = (d2 + datetime.timedelta(minutes=self.repete))
                sleep(0.010)

        self.base = d2 #configura o novo valor

    #depois de uma execução, verifica se a nova base é válida
    def valida_proxima(self, dataProxima:datetime) -> bool:
        retorno = False
        if not self.habilitada:
            return retorno

        #obtem a data atual
        d1 = dataProxima
        flag = -1

        #Lista que deverá ser preenchida a data da tarefa
        dt=[d1.year, flag, flag, flag, flag, d1.second]

        #----------------monta a data base--------------------
        if str(d1.month) in self.meses: dt[1] = d1.month
        
        if self.diasE != None:  #dias especificos
            if str(d1.day) in self.diasE: dt[2] = d1.day
        else:   #dias da semana
            if str(d1.weekday()) in self.dias: dt[2] = d1.day

        if str(d1.hour) in self.horas: dt[3] = d1.hour
        dt[4] = self.minutos
        #-----------------------------------------------------

        #verifica se todos os campos foram preenchidos
        if flag in dt:
            self.base = None
            return retorno
        
        return True

    #chama o processo a ser executado
    def abrir_processo(self):
        try:
            if self.escondido == 1:
                subprocess.Popen(self.comando, cwd=self.diretorio,creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(self.comando, cwd=self.diretorio)
        except:
            print(f'Ocorreu um erro ao tentar executar o processo da tarefa:{self.nome}')


    def executar(self):
        #se a data base nao foi definida, indica que o [mes] ou [dia] ou [hora]
        #não está dentro dos valores verificados
        if self.base == None and self.habilitada == True:
            #aqui deve-se chamar a função para localizar a base, porque o script poderá estar rodando
            #e se existir uma tarefa a ser executada num dia posterior, essa nao seria chamada
            self.data_base()
            return

        d1 = datetime.datetime.now()
        d2 = self.base        
        str1 = d1.strftime('%H:%M:%S')
        str2 = d2.strftime('%H:%M:%S')
        if str1 == str2:
            if self.repete > 0:
                dados_db.atualiza_campo(self.id, "ultima", str1) #atualiza ultima
                calcula_proxima = (d1 + datetime.timedelta(minutes=self.repete))
                self.abrir_processo()
                print(f'Tarefa: {self.nome}, executada as.: {str1}')
                if self.valida_proxima(calcula_proxima):
                    self.base = calcula_proxima  #ajusta para proxima
                    dados_db.atualiza_campo(self.id, "proxima", calcula_proxima.strftime('%H:%M:%S'))
                else:
                    self.base = None
                    dados_db.atualiza_campo(self.id, "proxima", str1)
            else:
                self.base = None    #reseta a base para verificar quando será a proxima
                dados_db.atualiza_campo(self.id, "ultima", str1)
                msg=f'Tarefa: {self.nome}, executada as.: {str1}'
                self.abrir_processo()
                print(f'Tarefa: {self.nome}, executada as.: {str1}')
#--fim class Trabalho

#extendendo a Class Timer de Thread
class Tarefa_Thread(Timer):
    def __init__(self, interval, function, reg:tuple) -> None:
        super().__init__(interval, function)
        self.tarefa = Trabalho(reg)
        self.setName(f'TH_{reg[0]}')    #cada thread terá como nome o prefixo TH_ + id do registro
        self.pid = os.getpid()
    def run(self):
        while not self.finished.wait(self.interval):
            try:
                self.tarefa.executar()
            except:
                break
        del self.tarefa #destroi o objeto ao finalizar
#--fim class Tarefa_Thread


#necessario para referência no thread
def funcao_dummy():
    pass

#cria, adiciona na lista e inicializa os threads
def inicializa_threads(listaTH:list, dados:list):
    for i in dados:
        if i[4] != 0: #só cria o thread, se estiver habilitado
            listaTH.append(Tarefa_Thread(1.0,funcao_dummy, i))

    for i in listaTH:
        i.start()
        print(f"Tarefa [{i.getName()}], iniciada... PID:{i.pid}")

#finaliza o thread especificado ou todos
def finaliza_threads(qual:str, listaTH:list) -> bool:
    if qual == 'todos':
        for i in listaTH:
            i.cancel()
            print(f"Tarefa [{i.getName()}], cancelada... PID:{i.pid}")
        listaTH.clear()
        return True
    
    #se [qual] for diferente de todos, remove pelo nome
    for i in range(0, len(listaTH)):
        th = listaTH[i]
        if th.getName() == f"TH_{qual}":
            th.cancel()
            listaTH.pop(i)
            del th
            print(f"Tarefa [{th.getName()}], cancelada...")
            break
    return True

#marcar/desmarcar campos
def selecionar_todos(janela:object, letra:str, qtd:int) -> None:
    """
    Marca ou Desmarca todos os campos do botão pressionado\n
    -> janela object - Referencia a janela criada\n
    -> letra str - Letra inicial das keys dos checkboxs\n
    -> qtd int - Quantidade de checkboxs\n
    <- return None - A função não retorna valores
    """
    inicio = 1
    fim = qtd + 1 #lembrando que range não retorna o ultimo numero
    if letra == 'h' or letra == 'd': #lembando que horas e dia da semana inicia em 0
        inicio = 0
        fim -= 1

    for i in range(inicio, fim):
        key=f'{letra}{i}'
        if janela[key].get():
            janela[key].update(False)
        else:
            janela[key].update(True)


#valida os campos minuto e repeticao
def verifica_valor(valor:str) -> str:
    if valor == None or len(valor) < 1: return '0'
    num = valor.strip()
    if len(num) < 1: return '0'
    if len(num) > 2: return '59'
    try:
        int_num = int(num)
    except:
        return '0'
    
    if int_num > 59: return '59'
    if int_num < 0: return '0'

    return str(int_num)

#limpa todos os campos da janela deixando num valor padrão
def resetar_campos(janela:object, todos:bool, valor:bool) -> None:
    """
    Reseta os campos da janela\n
    -> janela object - Referencia a janela criada\n
    -> todos bool - True reseta todos os campos, False reseta apenas os campos meses, dias, horas\n
    -> valor bool - Valor a ser atribuido aos campos meses, dias, horas\n
    <- None return - Essa função não retorna valores
    """
    if todos:
        janela['-ID-']('0')
        janela['txtNome']('')
        janela['txtTarefa']('')
        janela['txtMin']('0')
        janela['txtRep']('1')
        janela['-ESTADO-'].update(True)
        janela['txtEspecifico']('')
        janela['txtDiretorio']('')

    #meses
    for i in range(1,13):
        key = f'm{i}'
        janela[key].update(valor)
    
    #dias
    for i in range(0,7):
        key = f'd{i}'
        janela[key].update(valor)

    #horas
    for i in range(0,24):
        key = f'h{i}'
        janela[key].update(valor)    
    
    janela.refresh()

#deletar o registro informado
def deletar_tarefa(janela:object) -> bool:
    retorno = False
    id_str = janela['-ID-'].get()
    if len(id_str) < 1:
        sg.popup('Selecione uma Tarefa na lista para ser deletada.')
        return retorno
    try:
        id = int(id_str)
    except:
        sg.popup(f'Ocorreu um erro na conversão do id: {id_str}')
        return retorno

    retorno = dados_db.deleta_registro(id)
    if retorno == True:
        sg.popup(f'Tarefa de id: {id_str}, deletada com sucesso.')
    else:
        sg.popup(f'Ocorreu um erro ao tentar deletar a Tarefa de id: {id_str}.')

    return retorno


#salvar a tarefa
def salvar_tarefa(janela:object) -> bool:
    retorno = False
    nome = janela['txtNome'].get()
    tarefa = janela['txtTarefa'].get()
    diretorio = janela['txtDiretorio'].get()

    if len(nome.strip()) < 1:
        sg.popup('O campo [Nome da tarefa] não pode estar vazio')
        return retorno

    if len(tarefa.strip()) < 1:
        sg.popup('O campo [Tarefa] não pode estar vazio')
        return retorno

    if len(diretorio.strip()) > 0:
        if not os.path.exists(diretorio):
            sg.popup('O campo [Diretório de Trabalho], não contém um valor válido')
            return retorno

    meses = ''
    for i in range(1,13):
        key = f'm{i}'
        if janela[key].get():
            meses += str(i) + ','
    if len(meses) == 0: #deve haver pelo menos 1 mes selecionado
        sg.popup('Para salvar deve haver pelo menos 1 mês do ano selecionado')
        return retorno
    else:               #remove a ultima virgula adicionada
        meses = ''.join(meses.rsplit(',', 1))

    dias = ''
    for i in range(0, 7):
        key = f'd{i}'
        if janela[key].get():
            dias += str(i) + ','
    if len(dias) == 0: #deve haver pelo menos 1 dia selecionado
        sg.popup('Para salvar deve haver pelo menos 1 dia da semana selecionado')
        return retorno
    else:               #remove a ultima virgula adicionada
        dias = ''.join(dias.rsplit(',', 1))

    horas = ''
    for i in range(0, 24):
        key = f'h{i}'
        if janela[key].get():
            horas += str(i) + ','
    if len(horas) == 0: #deve haver pelo menos 1 hora selecionada
        sg.popup('Para salvar deve haver pelo menos 1 hora do dia selecionado')
        return retorno
    else:               #remove a ultima virgula adicionada
        horas = ''.join(horas.rsplit(',', 1))

    minutos = int(janela['txtMin'].get())
    repetir = int(janela['txtRep'].get())
    estado = int(janela['-ESTADO-'].get())
    ultimo = '00:00:00'
    proximo = '00:00:00'

    especifico = janela['txtEspecifico'].get()
    if len(especifico) > 0:
        msg = 'O campo [Dias Especificos] deve conter apenas numeros de [1 até 31] e separados por virgulas'
        separa = especifico.split(',')
        try:
            for i in separa:
                if int(i) < 1 or int(i) > 31:
                    sg.popup(msg)
                    return retorno
                
                if i.startswith('0'):
                    sg.popup(msg)
                    return retorno
        except:
            sg.popup(msg)
            return retorno

    ja_existe = dados_db.localiza_registro(nome)
    if ja_existe == None:
        retorno = dados_db.adiciona_registro(nome,tarefa,meses,dias,horas,minutos,repetir,ultimo,proximo,estado,especifico,diretorio)
        if retorno == True:
            sg.popup('Os dados foram gravados com sucesso.')
            return retorno
        else:
            sg.popup('Ocorreu um erro ao tentar salvar o registro')
            return retorno
    
    #se um registro com o memso nome já existir
    # pergunta se é para atualizar
    msg='Já existe uma tarefa com esse nome.\nClicando em [Yes], você estará atualizando o registro\n'
    msg+='Clicando em [No] ou fechando esse dialogo, nada será alterado\n'
    msg+='Caso deseje criar um novo resistro, basta dar outro nome a essa tarefa.'
    questao = sg.popup_yes_no(msg, title='ATENÇÂO!!!')
    if questao == 'Yes' or questao == 'Sim':
        retorno = dados_db.atualiza_registro(ja_existe,nome,tarefa,meses,dias,horas,minutos,repetir,ultimo,proximo,estado,especifico,diretorio)
        if retorno == True:
            sg.popup(f'A tarefa: {nome}, com Id: {ja_existe}, foi atualizada com sucesso.')
        else:
            sg.popup(f'Não foi possivel atualizar a tarefa: {nome}, com Id: {ja_existe}')
    else:
        sg.popup('Atualização cancelada.')

    return retorno

#carrega os dados nos campos apropriados
#id, nome, ultima, proxima, estado, tarefa, meses, dias, horas, minutos, repetir, especifico, diretorio
def editar_tarefa(janela:object, id:int, dados:list) -> None:
    
    #desmarca os valores de meses, dias, horas
    resetar_campos(janela, True, False)
  
    linha = dados[id]
    janela['-ID-'](linha[0])
    janela['txtNome'](linha[1])
    janela['txtTarefa'](linha[5])
    janela['txtMin'](linha[9])
    janela['txtRep'](linha[10])
    janela['txtEspecifico'](linha[11])
    janela['txtDiretorio'](linha[12])

    estado = linha[4]
    if estado == 1:
        janela['-ESTADO-'].update(True)
    else:
        janela['-ESTADO-'].update(False)

    #meses
    meses = linha[6].split(',')
    for i in meses: #atribui os valores 
        key = f'm{i}'
        janela[key].update(True)

    #dias
    dias = linha[7].split(',')    
    for i in dias: #atribui os valores 
        key = f'd{i}'
        janela[key].update(True)

    #horas
    horas = linha[8].split(',')    
    for i in horas: #atribui os valores 
        key = f'h{i}'
        janela[key].update(True)

#---------------------------------------------inicio------------------------------------------------------------
def main():
    #cria o banco de dados e tabela caso nao exista
    if not dados_db.cria_tabela():
        sg.popup(f'Ocorreu um erro ao tentar criar o banco de dados e a tabela.')
        exit()

    #coleta os dados do banco de dados para montar a tabela
    dados = dados_db.retorna_registro(0)

    #monta os checkbox dos meses, dias e horas
    cb_meses = [[sg.Checkbox(text='Jan',default=True, key='m1'), sg.Checkbox(text='Fev',default=True,key='m2'),
                sg.Checkbox(text='Mar',default=True, key='m3'), sg.Checkbox(text='Abr',default=True,key='m4'),
                sg.Checkbox(text='Mai',default=True, key='m5'), sg.Checkbox(text='Jun',default=True,key='m6'),
                sg.Checkbox(text='Jul',default=True, key='m7'), sg.Checkbox(text='Ago',default=True,key='m8'),
                sg.Checkbox(text='Set',default=True, key='m9'), sg.Checkbox(text='Out',default=True,key='m10'),
                sg.Checkbox(text='Nov',default=True, key='m11'), sg.Checkbox(text='Dez',default=True,key='m12')]]

    cb_dias=[[sg.Checkbox(text='Seg',default=True, key='d0'), sg.Checkbox(text='Ter',default=True,key='d1'),
            sg.Checkbox(text='Qua',default=True, key='d2'), sg.Checkbox(text='Qui',default=True,key='d3'),
            sg.Checkbox(text='Sex',default=True, key='d4'), sg.Checkbox(text='Sab',default=True,key='d5'),
            sg.Checkbox(text='Dom',default=True, key='d6')]]

    cb_horas=[[
                sg.Checkbox(text='00',default=True, key='h0'), sg.Checkbox(text='01',default=True,key='h1'),
                sg.Checkbox(text='02',default=True, key='h2'), sg.Checkbox(text='03',default=True,key='h3'),
                sg.Checkbox(text='04',default=True, key='h4'), sg.Checkbox(text='05',default=True,key='h5'),
                sg.Checkbox(text='06',default=True, key='h6'), sg.Checkbox(text='07',default=True,key='h7'),
                sg.Checkbox(text='08',default=True, key='h8'), sg.Checkbox(text='09',default=True,key='h9'),
                sg.Checkbox(text='10',default=True, key='h10'), sg.Checkbox(text='11',default=True,key='h11')],
                [
                sg.Checkbox(text='12',default=True, key='h12'), sg.Checkbox(text='13',default=True,key='h13'),
                sg.Checkbox(text='14',default=True, key='h14'), sg.Checkbox(text='15',default=True,key='h15'),
                sg.Checkbox(text='16',default=True, key='h16'), sg.Checkbox(text='17',default=True,key='h17'),
                sg.Checkbox(text='18',default=True, key='h18'), sg.Checkbox(text='19',default=True,key='h19'),
                sg.Checkbox(text='20',default=True, key='h20'), sg.Checkbox(text='21',default=True,key='h21'),
                sg.Checkbox(text='22',default=True, key='h22'), sg.Checkbox(text='23',default=True,key='h23')            
                ]]

    #tooltips
    dica_0 = " Os dias devem ser separados por vírgulas.\nExemplo: 1,12,23,etc... " 
    dica_1 = " Se o valor for 0 (zero), a tarefa será executada apenas 1 vez\n nos dias e horas selecionados. "
    
    dias_especificos =[[sg.Input(size=(30,1),key='txtEspecifico', tooltip=dica_0)]]

    #meses, dias, horas
    frame_meses = [[sg.Button('Todos',key='-TDM-'), sg.Frame('Selecione os meses', cb_meses)]]
    frame_dias = [[sg.Button('Todos',key='-TDD-'), sg.Frame('Selecione os dias da semana ou', cb_dias),sg.Frame('Dias especificos', dias_especificos)]]
    frame_horas = [[sg.Button('Todas',key='-TDH-'), sg.Frame('Selecione as horas', cb_horas)]]

    #minuto e repetição
    l_col =[[sg.Text('Informe os minutos de inicio')],[sg.Input(size=(30,1), default_text='0',enable_events=True, key='txtMin')]]
    r_col =[[sg.Text('Repetir a cada quantos minuto')],[sg.Input(size=(30,1), default_text='1',enable_events=True, key='txtRep', tooltip=dica_1), sg.Checkbox(text='Habilitar',default=True, key='-ESTADO-')]]

    #tarefa, nome, salvar deletar
    tarefa = [[sg.Text('Tarefa a ser executada')],[sg.Input(size=(70,1), key='txtTarefa'), sg.FileBrowse('Localizar', key='-EXECUTAVEL-')]]
    tarefa_dir = [[sg.Text('Diretório de trabalho')],[sg.Input(size=(70,1), key='txtDiretorio'), sg.FolderBrowse('Localizar', key='-DIRETORIO-')]]
    tarefa_nome=[[sg.Text('Informe um nome para essa tarefa')],[sg.Input(size=(70,1), key='txtNome'), sg.Button('Salvar', key='-SALVAR-'),sg.Button('Deletar', key='-DELETAR-')]]

    cabecalho = ['Reg Id','Nome da Tarefa', 'Ultimo', 'Proximo','Habilitada']#, 'Tarefa','Meses','Dias','Horas', 'Minutos', 'Repetir', 'Especificos', 'Diretorio']
    tarefa_lista=[[sg.Button('Atualizar', key='-ATUALIZA_LISTA-'),sg.Text('Lista das tarefas salvas')],[sg.Table(values=dados,
                        headings=cabecalho,
                        max_col_width=25,
                        auto_size_columns=True,
                        expand_x=True,
                        expand_y=True,
                        justification='left',
                        row_height=20,
                        enable_events = True,
                        key='-TABELA-',
                        select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                        alternating_row_color='blue',
                        num_rows=min(len(dados), 20))],
                    [sg.Multiline(size=(100, 5), write_only=True, key='ML_LOG', reroute_stdout=True, echo_stdout_stderr=True, expand_x=True)]    
                ]

    layout = [[frame_meses],[frame_dias],[frame_horas], [sg.Column(l_col), sg.Column(r_col)], tarefa, tarefa_dir, tarefa_nome, tarefa_lista,[sg.Input(size=(10,1),key='-ID-',visible=False)]]
    window = sg.Window('Agendador de Tarefas', layout, font="_ 10", size=(900,800),resizable=True, finalize=True)

    
    lista_thread = []   #lista que será preenchida com os threads
    inicializa_threads(lista_thread, dados) #inicializa todas as tarefas com estado de habilitada
    #------------------------------- loop principal do script
    while True:
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED or event == 'Exit':
            finaliza_threads('todos',lista_thread)
            break

        #botões marcar/desmarcar todas    
        if event == '-TDM-':
            selecionar_todos(window,'m', 12)
        elif event == '-TDD-':
            selecionar_todos(window,'d', 7)
        elif event == '-TDH-':
            selecionar_todos(window,'h', 24)        
        
        #verifica os campos minuto e repetição
        elif event == 'txtMin':
            testa = verifica_valor(values['txtMin'])
            window['txtMin'].update(testa)    
        elif event == 'txtRep':
            testa = verifica_valor(values['txtRep'])
            window['txtRep'].update(testa)

        elif event == '-SALVAR-':
            salvar = salvar_tarefa(window)
            if salvar == True:
                dados = dados_db.retorna_registro(0)
                window['-TABELA-'].update(values=dados)
                resetar_campos(window, True, True)
                #reinicia os thread
                finaliza_threads('todos',lista_thread)
                inicializa_threads(lista_thread, dados)

        elif event == '-DELETAR-':
            deletar = deletar_tarefa(window)
            if deletar == True:
                dados = dados_db.retorna_registro(0)
                window['-TABELA-'].update(values=dados)
                resetar_campos(window, True, True)
                #reinicia os thread
                finaliza_threads('todos', lista_thread)
                inicializa_threads(lista_thread, dados)

        #ao clicar em uma linha da tabela
        elif event == "-TABELA-":
            selecionada = values['-TABELA-'][0]
            editar_tarefa(window, selecionada, dados)

        elif event == '-ATUALIZA_LISTA-':
            dados = dados_db.retorna_registro(0)
            window['-TABELA-'].update(values=dados)

        try:
            pass
        except KeyboardInterrupt:
            finaliza_threads('todos', lista_thread)
            break

    window.close()
#-- fim main()


if __name__ == '__main__':
    main()