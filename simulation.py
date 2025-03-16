import json
import pyglet
from pyglet.window import key
from pyglet.graphics import Batch
import math
import heapq

class MapViewer(pyglet.window.Window):
    def __init__(self, width=800, height=600):
        super().__init__(width, height, "Map Viewer")
        self.batch = pyglet.graphics.Batch()
        self.points = []
        self.connections = []
        self.zoom = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.move_speed = 20
        self.square_size = 15
        self.square_speed = 100 
        self.path = []
        self.current_path_index = 0
        self.current_segment_progress = 0
        self.background = pyglet.shapes.Rectangle(0, 0, width, height, color=(255, 255, 255), batch=self.batch)
        self.load_from_json()
        self.calculate_furthest_points_and_path()
        pyglet.clock.schedule_interval(self.update, 1/60.0)
        
    def load_from_json(self):
        try:
            with open("points_data.json", "r") as json_file:
                data = json.load(json_file)
            
            points_dict = {}
            for i, point_data in enumerate(data):
                x, y = point_data["x"], point_data["y"]
                point = {"id": i, "x": x, "y": y, "connections": []}
                points_dict[(x, y)] = point
                self.points.append(point)
            
            processed_connections = set()
            
            for point_data in data:
                x, y = point_data["x"], point_data["y"]
                current_point = points_dict[(x, y)]
                
                for conn in point_data["connections_normal"]:
                    target_x, target_y = conn["x"], conn["y"]
                    direction = conn.get("direction", [0, 0])
                    
                    if (target_x, target_y) in points_dict:
                        target_point = points_dict[(target_x, target_y)]
                        
                        conn_id = (current_point["id"], target_point["id"])
                        rev_conn_id = (target_point["id"], current_point["id"])
                        
                        if conn_id not in processed_connections and rev_conn_id not in processed_connections:
                            connection = {
                                "id": len(self.connections),
                                "start": current_point,
                                "end": target_point,
                                "dashed": False,
                                "direction": direction
                            }
                            self.connections.append(connection)
                            processed_connections.add(conn_id)
                            
                            current_point["connections"].append({"point": target_point, "connection": connection})
                            target_point["connections"].append({"point": current_point, "connection": connection})
                
                for conn in point_data["connections_dashed"]:
                    target_x, target_y = conn["x"], conn["y"]
                    direction = conn.get("direction", [0, 0])
                    
                    if (target_x, target_y) in points_dict:
                        target_point = points_dict[(target_x, target_y)]
                        
                        conn_id = (current_point["id"], target_point["id"])
                        rev_conn_id = (target_point["id"], current_point["id"])
                        
                        if conn_id not in processed_connections and rev_conn_id not in processed_connections:
                            connection = {
                                "id": len(self.connections),
                                "start": current_point,
                                "end": target_point,
                                "dashed": True,
                                "direction": direction
                            }
                            self.connections.append(connection)
                            processed_connections.add(conn_id)
                            
                            current_point["connections"].append({"point": target_point, "connection": connection})
                            target_point["connections"].append({"point": current_point, "connection": connection})
            
            print(f"Loaded {len(self.points)} points and {len(self.connections)} connections")
        except FileNotFoundError:
            print("File points_data.json not found")
        except json.JSONDecodeError:
            print("Error in JSON format")
        except Exception as e:
            print(f"Error loading data: {str(e)}")
    
    def calculate_furthest_points_and_path(self):
        if len(self.points) < 2:
            return
        
        max_distance = 0
        start_point = None
        end_point = None
        
        for i, p1 in enumerate(self.points):
            for j, p2 in enumerate(self.points[i+1:], i+1):
                distance = math.sqrt((p1["x"] - p2["x"])**2 + (p1["y"] - p2["y"])**2)
                if distance > max_distance:
                    max_distance = distance
                    start_point = p1
                    end_point = p2
        
        if start_point and end_point:
            print(f"Furthest points: ({start_point['x']}, {start_point['y']}) and ({end_point['x']}, {end_point['y']})")
            self.path = self.find_path(start_point, end_point)
            
            if self.path:
                self.square_pos = {"x": self.path[0]["x"], "y": self.path[0]["y"]}
                print(f"Path found with {len(self.path)} points")
            else:
                print("No path found between furthest points")
                if self.points:
                    self.square_pos = {"x": self.points[0]["x"], "y": self.points[0]["y"]}
    
    def find_path(self, start, end):
        distances = {}
        previous = {}
        unvisited = []
        visited = set()
        
        for point in self.points:
            point_id = point["id"]
            distances[point_id] = float('infinity')
            previous[point_id] = None
            
        distances[start["id"]] = 0
        heapq.heappush(unvisited, (0, start["id"]))
        
        while unvisited:
            current_distance, current_id = heapq.heappop(unvisited)
            
            if current_id == end["id"]:
                break
            if current_id in visited:
                continue
                
            visited.add(current_id)
            
            current_point = next(p for p in self.points if p["id"] == current_id)
            
            for connection in current_point["connections"]:
                neighbor = connection["point"]
                neighbor_id = neighbor["id"]
                
                if neighbor_id in visited:
                    continue
                    
                distance = current_distance + math.sqrt(
                    (current_point["x"] - neighbor["x"])**2 + 
                    (current_point["y"] - neighbor["y"])**2
                )
                
                if distance < distances[neighbor_id]:
                    distances[neighbor_id] = distance
                    previous[neighbor_id] = current_id
                    heapq.heappush(unvisited, (distance, neighbor_id))
        
        path = []
        current_id = end["id"]
        
        while current_id is not None:
            current_point = next(p for p in self.points if p["id"] == current_id)
            path.append(current_point)
            current_id = previous[current_id]
        
        return path[::-1]
    
    def on_draw(self):
        self.clear()
        self.batch.draw()
        
        for conn in self.connections:
            start_x = (conn["start"]["x"] + self.offset_x) * self.zoom + self.width // 2
            start_y = (conn["start"]["y"] + self.offset_y) * self.zoom + self.height // 2
            end_x = (conn["end"]["x"] + self.offset_x) * self.zoom + self.width // 2
            end_y = (conn["end"]["y"] + self.offset_y) * self.zoom + self.height // 2
            
            if conn["dashed"]:
                self.draw_dashed_line(start_x, start_y, end_x, end_y, color=(128, 128, 128), thickness=4)
            else:
                pyglet.shapes.Line(start_x, start_y, end_x, end_y, 
                                  color=(128, 128, 128), thickness=4, batch=None).draw()
            
            dx = end_x - start_x
            dy = end_y - start_y
            
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            
            arrow_size = 10
            length = math.sqrt(dx*dx + dy*dy)
            
            if length > 0:
                nx, ny = dx/length, dy/length
                
                arrow_p1_x = mid_x - nx * arrow_size - ny * arrow_size / 2
                arrow_p1_y = mid_y - ny * arrow_size + nx * arrow_size / 2
                arrow_p2_x = mid_x - nx * arrow_size + ny * arrow_size / 2
                arrow_p2_y = mid_y - ny * arrow_size - nx * arrow_size / 2
                
                pyglet.shapes.Triangle(mid_x, mid_y, arrow_p1_x, arrow_p1_y, arrow_p2_x, arrow_p2_y,
                                      color=(0, 0, 0), batch=None).draw()
    
        for point in self.points:
            x = (point["x"] + self.offset_x) * self.zoom + self.width // 2
            y = (point["y"] + self.offset_y) * self.zoom + self.height // 2
            pyglet.shapes.Circle(x, y, 5, color=(0, 0, 255), batch=None).draw()
        
        if hasattr(self, 'square_pos'):
            square_x = (self.square_pos["x"] + self.offset_x) * self.zoom + self.width // 2 - self.square_size / 2
            square_y = (self.square_pos["y"] + self.offset_y) * self.zoom + self.height // 2 - self.square_size / 2
            pyglet.shapes.Rectangle(square_x, square_y, self.square_size, self.square_size, 
                                  color=(255, 0, 0), batch=None).draw()
    
    def draw_dashed_line(self, x1, y1, x2, y2, color=(128, 128, 128), thickness=4):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            return
        
        nx, ny = dx / length, dy / length
        
        dash_length = 10
        gap_length = 10
        pos = 0
        
        while pos < length:
            end_pos = min(pos + dash_length, length)
            dash_x1 = x1 + nx * pos
            dash_y1 = y1 + ny * pos
            dash_x2 = x1 + nx * end_pos
            dash_y2 = y1 + ny * end_pos
            
            pyglet.shapes.Line(dash_x1, dash_y1, dash_x2, dash_y2, 
                              color=color, thickness=thickness, batch=None).draw()
            
            pos = end_pos + gap_length
    
    def on_key_press(self, symbol, modifiers):
        if symbol == key.W:
            self.offset_y -= self.move_speed / self.zoom
        elif symbol == key.S:
            self.offset_y += self.move_speed / self.zoom
        elif symbol == key.A:
            self.offset_x += self.move_speed / self.zoom
        elif symbol == key.D:
            self.offset_x -= self.move_speed / self.zoom
        elif symbol == key.ESCAPE:
            self.close()
    
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        zoom_factor = 1.2
        if scroll_y > 0:
            self.zoom *= zoom_factor
        else:
            self.zoom /= zoom_factor
    
    def update(self, dt):
        if not hasattr(self, 'square_pos') or not self.path or len(self.path) < 2:
            return
            
        current = self.path[self.current_path_index]
        next_point = self.path[self.current_path_index + 1]
        
        dx = next_point["x"] - current["x"]
        dy = next_point["y"] - current["y"]
        segment_length = math.sqrt(dx*dx + dy*dy)
        
        if segment_length > 0:
            self.current_segment_progress += self.square_speed * dt
            
            if self.current_segment_progress >= segment_length:
                self.current_segment_progress = 0
                self.current_path_index += 1

                if self.current_path_index >= len(self.path) - 1:
                    self.path.reverse()
                    self.current_path_index = 0

            progress_ratio = self.current_segment_progress / segment_length
            self.square_pos = {
                "x": current["x"] + dx * progress_ratio,
                "y": current["y"] + dy * progress_ratio
            }

if __name__ == "__main__":
    window = MapViewer()
    pyglet.app.run()