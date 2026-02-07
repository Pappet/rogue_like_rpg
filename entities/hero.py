class Hero:
    def __init__(self, name: str, hp: int, max_hp: int):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp

    def __repr__(self):
        return f"Hero(name={self.name}, hp={self.hp}/{self.max_hp})"
