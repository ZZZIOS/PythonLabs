import math

class Quaternion:
    def __init__(self, w, x, y, z):
        self.w = w
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, other):
        return Quaternion(
            self.w + other.w,
            self.x + other.x,
            self.y + other.y,
            self.z + other.z
        )

    def __mul__(self, other):
        new_w = self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z
        new_x = self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y
        new_y = self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x
        new_z = self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w
        return Quaternion(new_w, new_x, new_y, new_z)

    def conjugate(self):
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    def norm(self):
        return math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)

    def inverse(self):
        norm_sq = self.w**2 + self.x**2 + self.y**2 + self.z**2
        if norm_sq == 0:
            raise ValueError("Кватернион нулевой, обратный не существует")
        return Quaternion(self.w / norm_sq, -self.x / norm_sq, -self.y / norm_sq, -self.z / norm_sq)

    def normalize(self):
        n = self.norm()
        if n == 0:
            raise ValueError("Кватернион нулевой, нормализовать нельзя")
        return Quaternion(self.w / n, self.x / n, self.y / n, self.z / n)

    def rotate_vector(self, vector):
        v = Quaternion(0, vector[0], vector[1], vector[2])
        q_normalized = self.normalize()
        rotated = q_normalized * v * q_normalized.conjugate()
        return (rotated.x, rotated.y, rotated.z)

    @classmethod
    def from_axis_angle(cls, axis, angle_rad):
        x, y, z = axis
        n = math.sqrt(x**2 + y**2 + z**2)
        
        if math.isclose(n, 0.0):
            raise ValueError("Ось вращения не может быть нулевым вектором")
            
        x /= n
        y /= n
        z /= n

        half_angle = angle_rad / 2.0
        sin_half = math.sin(half_angle)
        
        return cls(
            w=math.cos(half_angle),
            x=x * sin_half,
            y=y * sin_half,
            z=z * sin_half
        ).normalize()

    def __str__(self):
        return f"Quaternion({self.w:.3f}, {self.x:.3f}, {self.y:.3f}, {self.z:.3f})"

if __name__ == "__main__":
    q1 = Quaternion(1, 0, 3, 0)
    q2 = Quaternion(0, 2, 0, 4)
    print(q1+q2)
    print(q2+q1)
    print(q1*q2)
    print(q2*q1)

    # Поворот вектора [1, 0, 0] на 90 градусов вокруг оси Y
    vector = [1, 0, 0]
    axis = (0, 1, 0)
    angle = math.pi / 2 
    q2 = Quaternion.from_axis_angle(axis, angle)
    rotated_vector2 = q2.rotate_vector(vector)
    print(rotated_vector2)