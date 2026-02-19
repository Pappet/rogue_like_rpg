from typing import List, Tuple
import esper
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from ecs.components import Position, Blocker
from map.map_container import MapContainer

class PathfindingService:
    @staticmethod
    def get_path(world, map_container: MapContainer, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Calculates a path from start to end using A* algorithm.
        
        Args:
            world: The esper World (or module in esper 3.x) to check for blockers.
            map_container: The current map container for terrain walkability.
            start: (x, y) starting coordinates.
            end: (x, y) target coordinates.
            
        Returns:
            A list of (x, y) coordinates representing the path, excluding the start point.
            Returns an empty list if no path is found.
        """
        width = map_container.width
        height = map_container.height
        
        if not (0 <= start[0] < width and 0 <= start[1] < height):
            return []
        if not (0 <= end[0] < width and 0 <= end[1] < height):
            return []

        # 1. Initialize matrix with map walkability (1 for walkable, 0 for blocked)
        # pathfinding library expects matrix[y][x]
        matrix = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(1 if map_container.is_walkable(x, y) else 0)
            matrix.append(row)
            
        # 2. Add entity blockers
        for ent, (pos, _) in world.get_components(Position, Blocker):
            if 0 <= pos.x < width and 0 <= pos.y < height:
                matrix[pos.y][pos.x] = 0
                
        # 3. Explicitly set destination as walkable (allowing pathing TO a target)
        dest_x, dest_y = end
        matrix[dest_y][dest_x] = 1
            
        # 4. Create Grid and Finder
        grid = Grid(matrix=matrix)
        start_node = grid.node(start[0], start[1])
        end_node = grid.node(end[0], end[1])
        
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        path, runs = finder.find_path(start_node, end_node, grid)
        
        # path is a list of Nodes, convert to (x, y) tuples and skip start
        if path and len(path) > 1:
            return [(node.x, node.y) for node in path[1:]]
        
        return []
