import math

class VisibilityService:
    @staticmethod
    def compute_visibility(origin, max_radius, transparency_func):
        """
        Computes visible coordinates from an origin up to a max radius.
        transparency_func: (x, y) -> bool (True if transparent)
        """
        visible = {origin}
        for octant in range(8):
            VisibilityService._cast_light(origin, 1, 1.0, 0.0, max_radius, octant, transparency_func, visible)
        return visible

    @staticmethod
    def _cast_light(origin, row, start, end, radius, octant, transparency_func, visible):
        if start < end:
            return
        
        radius_sq = radius * radius
        for j in range(row, radius + 1):
            dx, dy = -j, -j
            blocked = False
            while dx <= 0:
                l_slope, r_slope = (dx - 0.5) / (dy + 0.5), (dx + 0.5) / (dy - 0.5)
                if start < r_slope:
                    dx += 1
                    continue
                elif end > l_slope:
                    break
                else:
                    mx, my = VisibilityService._transform_octant(dx, dy, octant, origin)
                    # Our light beam is touching this square; light it:
                    if dx*dx + dy*dy <= radius_sq:
                        visible.add((mx, my))
                    
                    if blocked:
                        # we're scanning a row of blocked squares:
                        if not transparency_func(mx, my):
                            new_start = r_slope
                            dx += 1
                            continue
                        else:
                            blocked = False
                            start = new_start
                    else:
                        if not transparency_func(mx, my) and j < radius:
                            # This is a blocking square, start a child scan:
                            blocked = True
                            VisibilityService._cast_light(origin, j + 1, start, l_slope, radius, octant, transparency_func, visible)
                            new_start = r_slope
                dx += 1
            if blocked:
                break

    @staticmethod
    def _transform_octant(dx, dy, octant, origin):
        x, y = origin
        if octant == 0: return x + dx, y - dy
        if octant == 1: return x + dy, y - dx
        if octant == 2: return x + dy, y + dx
        if octant == 3: return x + dx, y + dy
        if octant == 4: return x - dx, y + dy
        if octant == 5: return x - dy, y + dx
        if octant == 6: return x - dy, y - dx
        if octant == 7: return x - dx, y - dy
        return x, y
