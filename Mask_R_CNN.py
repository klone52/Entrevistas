import detectron2
from detectron2.utils.logger import setup_logger
setup_logger()


from detectron2.data import DatasetCatalog, MetadataCatalog

# import some common detectron2 utilities
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog
from detectron2.data.datasets import register_coco_instances

import numpy as np
import cv2
import pickle
import os

class mask_RCNN:

    def __init__(self, data_name, path2json, path2img, weights_name="Weights/model_final.pth"):
        self.path2json = path2json
        self.path2img = path2img
        self.Data_Name = data_name
        if self.Data_Name+"_train" in DatasetCatalog.list():
            print("Dataset ya registrado")
            DatasetCatalog.remove(self.Data_Name+"_train")

        register_coco_instances(self.Data_Name+"_train", {}, self.path2json, self.path2img)

        cfg = get_cfg()
        cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))

        cfg.MODEL.WEIGHTS =  weights_name
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.4
        cfg.DATASETS.TEST = (self.Data_Name+"_train", )
        self.predictor = DefaultPredictor(cfg)

        self.walmart_metadata = MetadataCatalog.get(self.Data_Name+"_train")
        self.dataset_dicts = DatasetCatalog.get(self.Data_Name+"_train")

    def get_prediction(self, img):
        outputs = self.predictor(img)
        predictions = outputs["instances"]
        return predictions

    def get_mask(self, img, predictions, class_name, thresh = 0.9):
        #Entrega una imagen con todas las mascaras de la clase pedida que cumpla con el tresh
        mask = np.zeros((int(img.shape[0]), int(img.shape[1]), 1), np.uint8)


        for i, data in enumerate(predictions.pred_classes):
            #Para cada objeto en prediccion le corresponde un indice num de su clase
            num = data.item()
            if MetadataCatalog.get(self.Data_Name+"_train").thing_classes[num] == class_name:
                score=predictions.scores[i].item()
                if score >= thresh:
                    masks = predictions.pred_masks[i]
                    masks = masks.mul(255).byte().cpu().numpy()

                    cnt, _ = cv2.findContours(masks.copy(), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
                    cv2.drawContours(mask, cnt, -1, (255,255,255), -1)
                    x,y,w,h = cv2.boundingRect(cnt)
                    
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    fontScale = 1
                    color = (255, 0, 0)
                    thickness = 2
                    mask = cv2.putText(mask, str(score), (x,y), font, fontScale, color, thickness, cv2.LINE_AA) 

        return mask

    def get_contour(self, predictions, class_name, thresh = 0.9):
        cnt_list = list()
        #Revisar todas las predicciones
        for i, data in enumerate(predictions.pred_classes):
            num = data.item()
            # Revisar si numero de clase corresponde a clase buscada
            if MetadataCatalog.get(self.Data_Name+"_train").thing_classes[num] == class_name:
                score=predictions.scores[i].item()
                # print(class_name, score)
                #Revisar si la prediccion cumple con verosimilitud pedida
                if score >= thresh:
                    #Observar la mascara de item i de prediccion
                    masks =predictions.pred_masks[i]
                    masks = masks.mul(255).byte().cpu().numpy()
                    #Obtener el contorno del objeto encontrado
                    cnt, _ = cv2.findContours(masks.copy(), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
                    #Agregar contorno a lista de resultados
                    for i in cnt:
                        cnt_list.append(i)

        #Retornar una lista con todos los contornos de la clase buscada
        return cnt_list



    def load_obj(self, name):
        with open(name, 'rb') as f:
            return pickle.load(f)
