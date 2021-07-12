from multiprocessing import Process
import os
import time
import datetime
import pytz
import logging
import logging.config
import yaml

import select, socket, sys, queue


from kafka import TopicPartition, KafkaConsumer


class POS_Consumer:

    """
    Kafka se encarga de recibir los datos enviados para determinar el final de la compra

    TODO: actualmente sólo se están enviando sólo los datos de una sola caja y actualmente
    la clase sólo está diseñada para recibir solo de un desde un servidor, por lo que
    se deberá modificar el código para poder recibir desde otras direcciones

    """

    def __init__(self,config, queue_reader):

        """
        Inicialización de variables
        """

        self.config = config
        self.queue_reader = queue_reader
        self.timezone = pytz.timezone(config['Timezone'])
        self.numero_local = config['Building']
        self.kafka_state = False
        self.message_arrive = False
        self.Purchase_state = 0 #0 -> no hay nadie comprando
                                #1 -> Persona comprando
                                #2 -> Persona pagando
                                #3 -> Persona retirandose
        self.meson_num = 0	#Numero del meson del que se recibe mensaje
        self.msg_prev = ''

    def init_socket_server(self):
        """
        Inicialización de Kafka
        """
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setblocking(0)
        try:
            server.bind((self.config['PC']['IP_MASTER'], 50000))
            return True
        except:
            return False

        server.listen(10)
        inputs = [server]
        outputs = []
        message_queues = {}

    def Start(self):

        """
        Creación e inicio del nuevo proceso
        """

        kafka = Process(target=self.run, args=(self.queue_reader,))
        kafka.start()

        return kafka

    def decode_pos(self, pos):
        return (pos-84)
    
    def get_purchase_state(self, msg_raw):
        if msg_raw:
            if 'message name="EndTransaction"' in msg_raw:
                purchase_state=4
            elif 'message name="StartTransaction"' in msg_raw:
                purchase_state=1
            elif 'message name="EnterTenderMode"' in msg_raw:
                purchase_state=2
            elif 'message name="Receipt"' in msg_raw:
                purchase_state=3
            else:
                purchase_state=0
        return purchase_state

    def run(self, queue_reader):

        """
        Run actua de forma bloqueante, es decir a menos que le llegue un nuevo mensaje
        no continua su ejecución.

        En caso de llegar un mensaje nuevo, se determina si corresponde a un fin de compra,
        de ser el caso, se envía una señal al módulo reader.

        """
        # Carga config de logger
        with open('logger_config.yaml', 'r') as stream:
            log_config = yaml.load(stream, Loader=yaml.FullLoader)

        # Create logger
        logger = logging.getLogger('SCO_Alerts')
        logging.config.dictConfig(log_config)

        logger.info("Configuración OK")

        # socket_state = self.init_socket_server()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setblocking(0)
        host_ip =  socket.gethostbyname(socket.gethostname())
        port = self.config['SCO']['Socket_POS']
        try:
            server.bind((host_ip, port))
            logger.info(f"Inicalización de Server Socket: {host_ip}:{port}")
        except:
            logger.error(f"Inicalización de Server Socket Fallida")

        server.listen(10)
        inputs = [server]
        outputs = []
        message_queues = {}

        local_num = 0
        purchase_state = 0
        message_arrive = False

        purchase_state_prev = [0]*self.config['SCO']['Number_of_cameras'] 

        time.sleep(1) # Wait 1 sec

        while inputs:
            iter_init = time.time()
            readable, writable, exceptional = select.select(
                inputs, outputs, inputs)
            for s in readable:
                if s is server:
                    connection, client_address = s.accept()
                    logger.info(f'[+] Cliente POS Conectado: {client_address}')
                    connection.setblocking(0)
                    inputs.append(connection)
                    message_queues[connection] = queue.Queue()
                else:
                    data = s.recv(1024)
                    print(data)
                    if data:
                        data_split = data.decode('ascii').split('|')
                        local_num = int(data_split[0])
                        pos = int(data_split[1])
                        meson_num = self.decode_pos(pos)
                        correlative = int(data_split[2])
                        msg_raw = data_split[-1]


                        if local_num == self.numero_local:
                            if self.config['POS_Data']['Save_Log']:
                                try:
                                    path2save = self.config["Folder_2_Save_Files"]
                                    nombre_local = 'Local_'+ str(self.config["Building"])
                                    fecha = str(datetime.datetime.now(self.timezone).date())
                                    with open(path2save+nombre_local+'/'+fecha+'/Log_KafkaRaw.txt', 'a') as log_kafka:
                                        log_kafka.write(msg_raw)
                                except:
                                    logger.error('No se pudo guardar mensaje de POS')

                            purchase_state = self.get_purchase_state(msg_raw)
                            if purchase_state != 0 and (purchase_state_prev[meson_num-1] != purchase_state) and purchase_state != None :

                                logger.info(f'Local {local_num}, Caja {meson_num}, Estado Caja {purchase_state}')

                                if (purchase_state - purchase_state_prev[meson_num-1] > 1):
                                    print("ASISTIDO EN EL MESON:  ",meson_num)
                                    logger.debug(f'Incontinuidad de compra en caja {meson_num}, Estado Caja {purchase_state}, Estado de Caja Previo: {purchase_state_prev[meson_num-1]}')

                                else:
                                    if purchase_state == 2:
                                        print("Selección Método de Pago: Caja "+str(meson_num))
                                    elif purchase_state == 0:
                                        print("Compra Terminada: Caja "+str(meson_num))

                                    logger.info(f'Sending: Caja {meson_num}, Estado Caja {purchase_state}')
                                    queue_reader.put((message_arrive, purchase_state, meson_num))

                                print("PREV----> ",purchase_state_prev[meson_num-1])
                                print("ACT----> ",purchase_state)
                                purchase_state_prev[meson_num-1] = purchase_state

                                print("KAFKA:", purchase_state)
                                print("--Meson:", meson_num)                            

                        message_queues[s].put(data)
                        if s not in outputs:
                            outputs.append(s)
                    else:
                        if s in outputs:
                            outputs.remove(s)
                        inputs.remove(s)
                        s.close()
                        del message_queues[s]

            for s in writable:
                try:
                    next_msg = message_queues[s].get_nowait()
                except queue.Empty:
                    outputs.remove(s)
                else:
                    s.send(b'1\n')

            for s in exceptional:
                inputs.remove(s)
                if s in outputs:
                    outputs.remove(s)
                s.close()
                del message_queues[s]
