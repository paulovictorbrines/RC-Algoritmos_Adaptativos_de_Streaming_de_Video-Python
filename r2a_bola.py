# Alunos:
    # Kleber Rodrigues da Costa Júnior - 20/0053680;
    # Paulo Victor França de Souza - 20/0042548;
    # Thais Fernanda de Castro Garcia - 20/0043722.

# Disciplina:
    # Dep. Ciência da Computação - Universidade de Brasília (UnB),
    # Redes de Computadores - 2021.2, turma A.

# Implementação:
    # BOLA (Buffer Occupancy Base Lyapunov Algorithm).

##############################################################################################################################################

from r2a.ir2a import IR2A
from player.parser import *
from time import *
from base.whiteboard import *
from math import log
import math

##############################################################################################################################################

class R2A_BOLA(IR2A): # Classe do algoritmo BOLA 
                        # Utiliza informações sobre o buffer e fornece a qualidade do próximo segmento a ser baixado.
                        # De acordo com a vazão e/ou nível de buffer, seleciona automaticamente a maior qualidade possível a ser baixada.
                        # Evita travamentos ou re-buffering na transmissão.

    def __init__(self, id): # Método de inicialização.
        IR2A.__init__(self, id)
       
        self.whiteboard = Whiteboard.get_instance() # Estatísticas em tempo real geradas pela plataforma 
        self.parsed_mpd = '' # mpd é a extensão do arquivo de vídeo.
        self.lista_qi = [] # Quality index (endereço da qualidade).
        self.tempo_requisição = 0 # Tempo de requisição.
        self.lista_vazões = [] # Lista de vazões.
        self.gamma = 5
        self.qd_max = 0
        self.r_agora = 0

    ##########################################################################################################################################

    def handle_xml_request(self, msg): # Trata a requisição do xml 
        self.tempo_requisição = perf_counter() # Tempo de requisição (tempo de desempenho, em segundos).

        self.send_down(msg) # Requisição é de cima para baixo (deve-se enviar a mensagem para camada de baixo). 

    ##########################################################################################################################################

    def handle_xml_response(self, msg): # Trata a resposta do xml.
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.lista_qi = self.parsed_mpd.get_qi() # Lista de qualidades (self.lista_qi) é criada através do parser feito no conteúdo do arquivo mpd
         
        self.lista_vazões.append(msg.get_bit_length() / (perf_counter() - self.tempo_requisição)) # Calcula a vazão e coloca ela na lista de vazões.

        self.send_up(msg) # Resposta é de baixo para cima (deve-se enviar a mensagem para camada de cima). 

    ##########################################################################################################################################

    def handle_segment_size_request(self, msg): # Recebe como parâmetro uma msg do tipo base.SSMessage (requisição de a um segmento de vídeo (ss)).
        self.tempo_requisição = perf_counter() # Tempo de requisição.

        t = min(msg.get_segment_id(), 596 - msg.get_segment_id()) # 596 é a duração total do filme em segundos.
        t_linha = max(t/2, 3*msg.get_segment_size())
        qd_max = min(self.whiteboard.get_max_buffer_size(), t_linha) 
        self.V = (qd_max - 1)/(log(self.lista_qi[-1]/self.lista_qi[0]) + self.gamma) 

        buffer = self.whiteboard.get_playback_buffer_size()

        if len(buffer) > 0:
            bufferSize = buffer[-1][1]
        else:
            bufferSize = 0

        prev = -math.inf
        m_line = 0
        idx = 0

        i = 0
        while i < len(self.lista_qi):
            if (self.V*log(self.lista_qi[i]/self.lista_qi[0]) + self.V*self.gamma - bufferSize) / self.lista_qi[i] >= prev:
                prev = (self.V*log(self.lista_qi[i]/self.lista_qi[0]) + self.V*self.gamma - bufferSize) / self.lista_qi[i]
                idx = i 
            if self.lista_qi[i] <= max(self.lista_vazões[-1], self.lista_qi[0]):
                m_line = i
            i+=1
        
        if idx >= self.r_agora: 
            if m_line >= idx:
                m_line = idx
            elif m_line < self.r_agora:
                m_line = self.r_agora
            else:
                m_line += 1

            idx = m_line
        
        self.r_agora = idx 
        msg.add_quality_id(self.lista_qi[self.r_agora])
    
        self.send_down(msg) # Requisição é de cima para baixo (deve-se enviar a mensagem para camada de baixo). 

    ##########################################################################################################################################

    def handle_segment_size_response(self, msg): # Recebe como parâmetro uma msg do tipo base.SSMessage (resposta para a requisição de um segmento de vídeo específico).
        self.lista_vazões.append(msg.get_bit_length() / (perf_counter() - self.tempo_requisição)) # Calcula a vazão e coloca ela na lista de vazões
        self.send_up(msg) # Resposta é de baixo para cima (deve-se enviar a mensagem para camada de cima). 

    ##########################################################################################################################################

    def initialize(self):
        pass

    ##########################################################################################################################################

    def finalization(self):
        pass

