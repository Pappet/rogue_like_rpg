class _ShadowCaster:
    def __init__(self, origin, radius, octant, transparency_func, visible):
        self.origin = origin
        self.radius = radius
        self.radius_sq = radius * radius
        self.octant = octant
        self.transparency_func = transparency_func
        self.visible = visible

    def cast_light(self, row, start, end):
        if start < end:
            return

        for j in range(row, self.radius + 1):
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
                    mx, my = self._transform_octant(dx, dy)
                    # Our light beam is touching this square; light it:
                    if dx * dx + dy * dy <= self.radius_sq:
                        self.visible.add((mx, my))

                    if blocked:
                        # we're scanning a row of blocked squares:
                        if not self.transparency_func(mx, my):
                            new_start = r_slope
                            dx += 1
                            continue
                        else:
                            blocked = False
                            start = new_start
                    else:
                        if not self.transparency_func(mx, my) and j < self.radius:
                            # This is a blocking square, start a child scan:
                            blocked = True
                            self.cast_light(j + 1, start, l_slope)
                            new_start = r_slope
                dx += 1
            if blocked:
                break

    def _transform_octant(self, dx, dy):
        x, y = self.origin
        if self.octant == 0:
            return x + dx, y - dy
        if self.octant == 1:
            return x + dy, y - dx
        if self.octant == 2:
            return x + dy, y + dx
        if self.octant == 3:
            return x + dx, y + dy
        if self.octant == 4:
            return x - dx, y + dy
        if self.octant == 5:
            return x - dy, y + dx
        if self.octant == 6:
            return x - dy, y - dx
        if self.octant == 7:
            return x - dx, y - dy
        return x, y


class VisibilityService:
    @staticmethod
    def compute_visibility(origin, max_radius, transparency_func):
        """
        Computes visible coordinates from an origin up to a max radius.
        transparency_func: (x, y) -> bool (True if transparent)
        """
        visible = {origin}
        for octant in range(8):
            caster = _ShadowCaster(origin, max_radius, octant, transparency_func, visible)
            caster.cast_light(1, 1.0, 0.0)
        return visible
