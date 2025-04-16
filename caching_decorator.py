from abc import ABC, abstractmethod
from collections import OrderedDict, deque

class CacheStrategy(ABC):
    @abstractmethod
    def get(self, key):
        pass

    @abstractmethod
    def put(self, key, value):
        pass

class LRUCacheStrategy(CacheStrategy):
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.cache = OrderedDict()

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

class LFUCacheStrategy(CacheStrategy):
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.cache: Dict[tuple, object] = {}
        self.freq: Dict[tuple, int] = {}

    def get(self, key):
        if key in self.cache:
            self.freq[key] += 1
            return self.cache[key]
        return None

    def put(self, key, value):
        if key not in self.cache and len(self.cache) >= self.maxsize:
            min_key = min(self.freq, key=lambda k: self.freq[k])
            del self.cache[min_key]
            del self.freq[min_key]
        self.cache[key] = value
        self.freq[key] = self.freq.get(key, 0) + 1

class FIFOCacheStrategy(CacheStrategy):
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.cache: Dict[tuple, object] = {}
        self.queue = deque()

    def get(self, key):
        return self.cache.get(key)

    def put(self, key, value):
        if key not in self.cache:
            if len(self.cache) >= self.maxsize:
                oldest = self.queue.popleft()
                del self.cache[oldest]
            self.queue.append(key)
        self.cache[key] = value

def cached(maxsize = 10, strategy = "FIFO"):
    def decorator(func):
        match strategy:
            case "LRU":
                handler = LRUCacheStrategy(maxsize)
            case "LFU":
                handler = LFUCacheStrategy(maxsize)
            case "FIFO":
                handler = FIFOCacheStrategy(maxsize)
            case _:
                raise ValueError(f"Unknown strategy: {strategy}")

        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            
            result = handler.get(key)
            if result is not None:
                return result
                
            result = func(*args, **kwargs)
            handler.put(key, result)
            return result
            
        return wrapper
    return decorator

def main():
    # FIFO
    @cached(maxsize=2)
    def add(a, b):
        print("Вычисление...")
        return a + b

    print("FIFO Пример:")
    print(add(1, 2))  # Вычисление... 3
    print(add(1, 2))  # 3 (из кэша)
    print(add(3, 4))  # Вычисление... 7
    print(add(5, 6))  # Вычисление... 11 (вытеснение 1+2)
    print(add(1, 2))  # Вычисление... 3 (снова вычислено)
    print()

    # LRU
    @cached(maxsize=2, strategy="LRU")
    def upper(s):
        print("Обработка...")
        return s.upper()

    print("LRU Пример:")
    print(upper('a'))  # Обработка... 'A'
    print(upper('b'))  # Обработка... 'B'
    print(upper('a'))  # Из кэша (перемещён в конец)
    print(upper('c'))  # Обработка... 'C' (вытеснен 'b')
    print(upper('a'))  # Из кэша
    print(upper('b'))  # Обработка... (вытеснен 'c')
    print()

    # LFU
    @cached(maxsize=2, strategy="LFU")
    def square(x):
        print("Вычисление квадрата...")
        return x * x

    print("LFU Пример:")
    print(square(2))  # Вычисление... 4
    print(square(2))  # Из кэша (частота 2)
    print(square(3))  # Вычисление... 9 (кэш: 2(2), 3(1))
    print(square(4))  # Вычисление... 16 (вытеснен 3)
    print(square(2))  # Из кэша (частота 3)
    print(square(3))  # Вычисление... 9 (вытеснен 4)
    print()


if __name__ == "__main__":
    main()