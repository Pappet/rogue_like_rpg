class _ShadowCaster:
    def __init__(self, origin, radius, octant, transparency_func, visible):
        if octant == 0:
            self.xx, self.xy, self.yx, self.yy = 1, 0, 0, -1
        elif octant == 1:
            self.xx, self.xy, self.yx, self.yy = 0, 1, -1, 0
        elif octant == 2:
            self.xx, self.xy, self.yx, self.yy = 0, 1, 1, 0
        elif octant == 3:
            self.xx, self.xy, self.yx, self.yy = 1, 0, 0, 1
        elif octant == 4:
            self.xx, self.xy, self.yx, self.yy = -1, 0, 0, 1
        elif octant == 5:
            self.xx, self.xy, self.yx, self.yy = 0, -1, 1, 0
        elif octant == 6:
            self.xx, self.xy, self.yx, self.yy = 0, -1, -1, 0
        elif octant == 7:
            self.xx, self.xy, self.yx, self.yy = -1, 0, 0, -1

        self.ox, self.oy = origin
        self.radius = radius
        self.radius_sq = radius * radius
        self.transparency_func = transparency_func
        self.visible = visible

    def cast_light(self, row, start, end):
        if start < end:
            return

        # Cache local variables for fast lookup in inner loop
        xx, xy, yx, yy = self.xx, self.xy, self.yx, self.yy
        ox, oy = self.ox, self.oy
        transparency_func = self.transparency_func
        visible_add = self.visible.add
        radius = self.radius
        radius_sq = self.radius_sq
        cast_light = self.cast_light

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
                    mx, my = ox + dx * xx + dy * xy, oy + dx * yx + dy * yy
                    # Our light beam is touching this square; light it:
                    if dx * dx + dy * dy <= radius_sq:
                        visible_add((mx, my))

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
                            cast_light(j + 1, start, l_slope)
                            new_start = r_slope
                dx += 1
            if blocked:
                break


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
