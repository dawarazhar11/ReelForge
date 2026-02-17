from coldtype import *

@renderable()
def test(r):
    return P().oval(r)
 
if __name__ == "__main__":
    print("Running simplest Coldtype example")
    test.show() 