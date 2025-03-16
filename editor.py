import json
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsRectItem, QGraphicsPolygonItem
from PyQt6.QtGui import QPen, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QPointF
import sys
from PyQt6.QtGui import QPainter, QPen, QFont

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.connected_points_normal = []
        self.connected_points_dashed = []
        self.direction_normal = []
        self.direction_dashed = []

    def add_connection(self, other_point, is_dashed, direction):
        if is_dashed:
            self.connected_points_dashed.append(other_point)
            self.direction_dashed.append(direction)
        else:
            self.connected_points_normal.append(other_point)
            self.direction_normal.append(direction)

    def to_dict(self):
        connections_normal = [{"x": p.x, "y": p.y, "direction": dir} for p, dir in zip(self.connected_points_normal, self.direction_normal)]
        connections_dashed = [{"x": p.x, "y": p.y, "direction": dir} for p, dir in zip(self.connected_points_dashed, self.direction_dashed)]
        return {
            "x": self.x,
            "y": self.y,
            "connections_normal": connections_normal,
            "connections_dashed": connections_dashed
        }

from PyQt6.QtGui import QPixmap, QBrush

class MapEditor(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        self.points = []
        self.selected_point = None
        self.scale_factor = 1.2
        self.move_step = 20
        self.dashed_line = False
        
        self.load_background_image("photo.png")
        
        self.origin_square = QGraphicsRectItem(-5, -5, 10, 10)
        self.origin_square.setBrush(QBrush(Qt.GlobalColor.red))
        self.origin_square.setPen(QPen(Qt.GlobalColor.black))
        self.scene.addItem(self.origin_square)
    
    def load_background_image(self, image_path):
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                print(f"Nie udało się wczytać obrazu: {image_path}")
                return
                
            x_position = -pixmap.width() / 2
            y_position = -pixmap.height() / 2
            
            self.background_item = self.scene.addPixmap(pixmap)
            self.background_item.setPos(x_position, y_position)
            
            self.background_item.setZValue(-1)
            
            print(f"Wczytano obraz tła: {image_path}")
        except Exception as e:
            print(f"Błąd podczas wczytywania obrazu: {str(e)}")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.add_point(event.position())
        elif event.button() == Qt.MouseButton.RightButton:
            self.select_or_connect(event.position())
        
    def add_point(self, pos):
        scene_pos = self.mapToScene(pos.toPoint())
        point_item = QGraphicsEllipseItem(scene_pos.x() - 5, scene_pos.y() - 5, 10, 10)
        point_item.setBrush(QBrush(Qt.GlobalColor.blue))
        point_item.setPen(QPen(Qt.GlobalColor.black))
        point_item.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
        self.scene.addItem(point_item)

        point = Point(scene_pos.x(), scene_pos.y())
        self.points.append((point_item, point))
        
    def select_or_connect(self, pos):
        scene_pos = self.mapToScene(pos.toPoint())
        for point_item, point in self.points:
            if point_item.contains(scene_pos):
                if self.selected_point is None:
                    self.selected_point = (point_item, point)
                else:
                    self.connect_points(self.selected_point[1], point, self.dashed_line)
                    self.selected_point = None
                break
        
    def connect_points(self, p1, p2, is_dashed):
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        
        line = QGraphicsLineItem(x1, y1, x2, y2)
        pen = QPen(Qt.GlobalColor.black, 2)
        
        if is_dashed:
            pen.setStyle(Qt.PenStyle.DashLine)
        line.setPen(pen)
        
        self.scene.addItem(line)
        
        self.add_arrow(x1, y1, x2, y2)

        direction = (x2 - x1, y2 - y1)
        p1.add_connection(p2, is_dashed, direction)
        p2.add_connection(p1, is_dashed, (-direction[0], -direction[1]))

    def add_arrow(self, x1, y1, x2, y2):
        arrow_size = 10
        dx, dy = x2 - x1, y2 - y1
        length = (dx**2 + dy**2) ** 0.5
        if length == 0:
            return
        
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        unit_dx, unit_dy = dx / length, dy / length
        arrow_p1 = QPointF(mid_x - unit_dx * arrow_size - unit_dy * arrow_size / 2, 
                            mid_y - unit_dy * arrow_size + unit_dx * arrow_size / 2)
        arrow_p2 = QPointF(mid_x - unit_dx * arrow_size + unit_dy * arrow_size / 2, 
                            mid_y - unit_dy * arrow_size - unit_dx * arrow_size / 2)

        arrow_head = QPolygonF([QPointF(mid_x, mid_y), arrow_p1, arrow_p2])
        arrow_item = QGraphicsPolygonItem(arrow_head)
        arrow_item.setBrush(QBrush(Qt.GlobalColor.black))
        self.scene.addItem(arrow_item)
    
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(self.scale_factor, self.scale_factor)
        else:
            self.scale(1 / self.scale_factor, 1 / self.scale_factor)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_W:
            self.setSceneRect(self.sceneRect().translated(0, -self.move_step))
        elif event.key() == Qt.Key.Key_S:
            self.setSceneRect(self.sceneRect().translated(0, self.move_step))
        elif event.key() == Qt.Key.Key_A:
            self.setSceneRect(self.sceneRect().translated(-self.move_step, 0))
        elif event.key() == Qt.Key.Key_D:
            self.setSceneRect(self.sceneRect().translated(self.move_step, 0))
        elif event.key() == Qt.Key.Key_T: 
            self.toggle_line_type()
        elif event.key() == Qt.Key.Key_V:
            self.save_to_json()
        elif event.key() == Qt.Key.Key_B:
            self.load_from_json()
        elif event.key() == Qt.Key.Key_C:
            self.remove_overlapping_points()
    
    def remove_overlapping_points(self):
        min_distance = 10
        points_to_remove = []
        
        for i, (item1, point1) in enumerate(self.points):
            has_connections = (len(point1.connected_points_normal) > 0 or 
                            len(point1.connected_points_dashed) > 0)
            
            if has_connections:
                continue
                
            for j, (item2, point2) in enumerate(self.points):
                if i != j:
                    distance = ((point1.x - point2.x) ** 2 + (point1.y - point2.y) ** 2) ** 0.5
                    if distance < min_distance:
                        points_to_remove.append((item1, point1))
                        break
        
        for item, point in points_to_remove:
            self.scene.removeItem(item)
            self.points.remove((item, point))
        
        if points_to_remove:
            print(f"Usunięto {len(points_to_remove)} nachodzących punktów bez połączeń")
        else:
            print("Nie znaleziono nachodzących punktów bez połączeń")

    def toggle_line_type(self):
        self.dashed_line = not self.dashed_line
        self.update() 

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self.viewport())
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.setFont(QFont("Arial", 10))
        
        line_type = "Ciągła" if not self.dashed_line else "Przerywana"
        painter.drawText(10, 20, f"Aktualny typ linii: {line_type}")

    def save_to_json(self):
        data = [point.to_dict() for _, point in self.points]
        with open("points_data.json", "w") as json_file:
            json.dump(data, json_file, indent=4)
        print("Stan zapisany do pliku points_data.json")
    
    def load_from_json(self):
        try:
            with open("points_data.json", "r") as json_file:
                data = json.load(json_file)
            
            for item in self.scene.items():
                if item != self.origin_square:
                    self.scene.removeItem(item)
            
            self.points = []
            self.selected_point = None
            
            points_dict = {}
            
            for point_data in data:
                x, y = point_data["x"], point_data["y"]
                point_item = QGraphicsEllipseItem(x - 5, y - 5, 10, 10)
                point_item.setBrush(QBrush(Qt.GlobalColor.blue))
                point_item.setPen(QPen(Qt.GlobalColor.black))
                point_item.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable)
                self.scene.addItem(point_item)
                
                point = Point(x, y)
                self.points.append((point_item, point))
                points_dict[(x, y)] = point
            
            for point_data in data:
                x, y = point_data["x"], point_data["y"]
                current_point = points_dict[(x, y)]
                
                for conn in point_data["connections_normal"]:
                    target_x, target_y = conn["x"], conn["y"]
                    target_point = points_dict.get((target_x, target_y))
                    
                    if target_point:
                        if target_point not in current_point.connected_points_normal:
                            self.connect_points(current_point, target_point, False)
                
                for conn in point_data["connections_dashed"]:
                    target_x, target_y = conn["x"], conn["y"]
                    target_point = points_dict.get((target_x, target_y))
                    
                    if target_point:
                        if target_point not in current_point.connected_points_dashed:
                            self.connect_points(current_point, target_point, True)
            
            print("Mapa została wczytana z pliku points_data.json")
        except FileNotFoundError:
            print("Nie znaleziono pliku points_data.json")
        except json.JSONDecodeError:
            print("Błąd w formacie pliku JSON")
        except Exception as e:
            print(f"Wystąpił błąd podczas wczytywania: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapEditor()
    window.show()
    sys.exit(app.exec())
