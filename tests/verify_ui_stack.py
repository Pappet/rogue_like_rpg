from ui.stack_manager import UIStack
from ui.windows.base import UIWindow
import pygame

def test_stack():
    stack = UIStack()
    assert not stack.is_active()
    
    win1 = UIWindow((0, 0, 100, 100))
    stack.push(win1)
    assert stack.is_active()
    assert len(stack.stack) == 1
    
    win2 = UIWindow((10, 10, 50, 50))
    stack.push(win2)
    assert len(stack.stack) == 2
    
    popped = stack.pop()
    assert popped == win2
    assert len(stack.stack) == 1
    
    stack.pop()
    assert not stack.is_active()
    
    print("UIStack tests passed!")

if __name__ == "__main__":
    test_stack()
