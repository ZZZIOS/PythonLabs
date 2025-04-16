class Shape:
    """Геометрические фигуры"""
    name = 'геометрическая фигура'

    def __init__(self, x=0, y=0):
        self.__x = x
        self.__y = y

    def __repr__(self):
        return f"{self.name} по координатам ({self.__x}, {self.__y})"


class Rectangle(Shape):
    """Прямоугольники"""
    name = 'прямоугольник'

    def __init__(self, width, height, x=0, y=0):
        super().__init__(x, y)
        self._width = width
        self._height = height

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        if value < 0:
            raise ValueError("Ширина не может быть отрицательной")
        self._width = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        if value < 0:
            raise ValueError("Высота не может быть отрицательной")
        self._height = value

    def area(self):
        return self._width * self._height

    def perimeter(self):
        return 2 * (self._width + self._height)

    def __repr__(self):
        return (f"{super().__repr__()}, со сторонами {self._width} и {self._height}, "
                f"с площадью {self.area()} и периметром {self.perimeter()}")


class Square(Rectangle):
    """Квадраты"""
    name = 'квадрат'

    def __init__(self, side, x=0, y=0):
        super().__init__(side, side, x, y)

    def __repr__(self):
        return (f"{super().__repr__()}, со стороной {self._width}, "
                f"с площадью {self.area()} и периметром {self.perimeter()}")

    @Rectangle.width.setter
    def width(self, value):
        if value < 0:
            raise ValueError("Ширина не может быть отрицательной")
        self._width = value
        self._height = value

    @Rectangle.height.setter
    def height(self, value):
        if value < 0:
            raise ValueError("Высота не может быть отрицательной")
        self._height = value
        self._width = value


def unify_width(figures, new_width):
    """Устанавливает всем фигурам указанную ширину"""
    for figure in figures:
        figure.width = new_width


if __name__ == '__main__':
    figures = [Rectangle(2, 3), Square(2, 1, 1)]
    
    unify_width(figures, 5)
    
    for figure in figures:
        print(figure)

    figures[0].width = -2