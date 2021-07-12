from multiprocessing import Process
import os
import ast
import time
import logging
import logging.config
import yaml
# from Mask_R_CNN_Objetos import mask_RCNN_Objetos
# from Mask_R_CNN_Personas import mask_RCNN_Personas
from Mask_R_CNN import mask_RCNN
from Utility import *

class GPU():

    """
    GPU obtiene las mascaras de las personas cargando los pesos de las redes neuronales.
    Recibe las imágenes de reader y obtiene las máscaras de las personas, cables y pistola
    """
    def __init__(self, config, queue_reader, queue_judge):

        """
        Inicialización de variables
        """

        self.config = config
        # self.queue_Logging = queue_Logging
        self.queue_reader = queue_reader
        self.queue_judge = queue_judge

        """
        Configuración de valores desde el archivo de configuración
        """

        # Imágenes de la mascara de los mesones
        self.mask = config['SCO']["Number_of_cameras"]*[0]

        # Indica la cantidad de imágenes a analizar al finalizar la compra por cada cámara
        self.N_img_buffer = config['SCO']["Cam_Buffer"]

        #Camaras a procesar
        self.Cam2Process = config['SCO']["Cam2Process"]


    def init_GPU_Weights(self):
        """
        Cargar redes neuronales
        """
        self.Mask_RCNN_Meson = mask_RCNN(self.config['SCO']['Meson'][0], self.config['SCO']['Meson'][1], self.config['SCO']['Meson'][2], self.config['SCO']['Meson'][3])
        self.Mask_RCNN_Carro = mask_RCNN(self.config['SCO']['Carro'][0], self.config['SCO']['Carro'][1], self.config['SCO']['Carro'][2], self.config['SCO']['Carro'][3])

    def Start(self):

        """
        Inicializar y crear nuevo proceso
        """

        gpu = Process(target=self.run, args=(self.queue_reader, self.queue_judge))
        gpu.start()

        return gpu

    def run(self, queue_reader, queue_judge):

        """
        Run se encarga de recibir las imágenes provenientes de reader, obtener las máscaras
        de las personas, cables y pistolas, y enviarlas al módulo apply_mask
        """

        # Carga config de logger
        with open('logger_config.yaml', 'r') as stream:
            log_config = yaml.load(stream, Loader=yaml.FullLoader)

        # Create logger
        logger = logging.getLogger('SCO_Alerts')
        logging.config.dictConfig(log_config)

        # queue_Logging.put(("GPU: Configuracion de GPU", "INFO"))
        logger.info('Configuración OK')

        self.init_GPU_Weights()
        # queue_Logging.put(("GPU: Pesos de Red Neuronal cargados", "INFO"))
        logger.info('Pesos de Red Neuronal cargados')

        while True:
            cam, Buffer_Reader = queue_reader.get()
            iter_init = time.time()
            logger.info(f'Data recibida: Cámara {cam+1}')

            # queue_Logging.put(("GPU: Procesando datos", "INFO"))

            pred_MesonLleno = self.N_img_buffer*[0]
            pred_CarroLleno = self.N_img_buffer*[0]

            mask_MesonLleno = self.N_img_buffer*[0]
            mask_CarroLleno = self.N_img_buffer*[0]

            for i in range(len(Buffer_Reader)):
                # Se genera una prediccion en imagen Buffer_Reader[i]
                prediction_meson = self.Mask_RCNN_Meson.get_prediction(Buffer_Reader[i])
                prediction_carro = self.Mask_RCNN_Carro.get_prediction(Buffer_Reader[i])

                # Se obtienen mascaracas para cada elemento de interes con un threshold determinado
                # mask_MesonLleno[i] = self.Mask_RCNN_Walmart.get_mask(Buffer_Reader[i], prediction,"MesonLleno", 0.8)
                # mask_CarroLleno[i] = self.Mask_RCNN_Walmart.get_mask(prediction, "Lleno", 0.95)
                mask_MesonLleno[i] = self.Mask_RCNN_Meson.get_contour(prediction_meson,"MesonLleno", 1.99)
                mask_CarroLleno[i] = self.Mask_RCNN_Carro.get_contour(prediction_carro, "Lleno", 0.95)
            
            logger.info(f'Tiempo de Análisis: {time.time()-iter_init}')
            
            queue_judge.put((cam, Buffer_Reader, mask_MesonLleno, mask_CarroLleno))
            logger.info(f'Análisis enviado a juez, Cámara {cam+1}')
            
            logger.info(f'Tiempo de iteración: {time.time()-iter_init}')

            # queue_Logging.put(("GPU: Data enviada a Judge", "INFO"))
