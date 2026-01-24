import sys
import hmac
import math
import string
import secrets
import hashlib
from typing import MutableSequence,Any,List,Sequence,Iterable

class CryptographicRandom():
    def __init__(self,key:str=None,msg:str=None,nonce:int=1):
        self.key = key if key else self.generate_new_seed()
        self.msg = msg if msg else self.generate_new_seed(seed_length=20)
        self.nonce = nonce

    def _seeds_to_hexadecimals(self,num_messages=1) -> str|list[str]:
        if(not(isinstance(num_messages,int))):
            raise ValueError(f"num_messages parameter expected int type. {type(num_messages)} type passed.")
        if num_messages == 1:
            message:str = f"{self.msg}:{self.nonce}:0"
            hmac_obj:hmac.HMAC = hmac.new(self.key.encode(),message.encode(),hashlib.sha256)
            return hmac_obj.hexdigest()
        elif num_messages < 1:
            raise ValueError(f"num_messages must be greater than or equal to 1. {num_messages} was passed")
        else:
            hex_digests:list[str] = []
            for message_number in range(num_messages):
                message:str = f"{self.msg}:{self.nonce}:{message_number}"
                hmac_obj:hmac.HMAC = hmac.new(self.key.encode(),message.encode(),hashlib.sha256)
                hex_digests.append(hmac_obj.hexdigest())
            return hex_digests
    
    def _hexadecimal_to_bytes(self, hexadecimal:str|list[str]) -> list[int]|list[list[int]]:
        if isinstance(hexadecimal,str):
            return list(bytes.fromhex(hexadecimal))
        elif isinstance(hexadecimal,list):
            bytes_lists:list[list[int]] = []
            for current_hexadecimal in hexadecimal:
                bytes_lists.append(list(bytes.fromhex(current_hexadecimal)))
            return bytes_lists
        else:
            raise ValueError(f"Invalid hexadecimal type. Must be either str or list[str], {type(hexadecimal)} was passed.")
    
    def random(self,num_messages=1,allow_seed_rotation=False) -> float|list[float]:
        hexadecimals:str|list[str] = self._seeds_to_hexadecimals(num_messages=num_messages)
        hexadecimal_bytes:list[int]|list[list[int]] = self._hexadecimal_to_bytes(hexadecimal=hexadecimals)
        number:float = 0
        numbers:list[float] = []
        if isinstance(hexadecimal_bytes,list) and isinstance(hexadecimal_bytes[0],list):
            for current_hexadecimal_bytes in hexadecimal_bytes:
                for index,current_byte in enumerate(current_hexadecimal_bytes):
                    number += (float(current_byte) / float(256**(index+1))) 
                numbers.append(number)
                number:float = 0
        elif isinstance(hexadecimal_bytes,list):
            for index,current_byte in enumerate(hexadecimal_bytes):
                number += (float(current_byte) / float(256**(index+1))) 
        
        self.nonce += 1
        if self.nonce >= 1_000_000_000 and allow_seed_rotation:
            self.new_seeds()
        if numbers:
            return numbers
        return number
    
    def randint(self, a:int, b:int, num_messages=1) -> int|list[int]:
        """Obtain a provably, verifiably fair random integer between a (inclusive) and b (exclusive)"""
        if(not(isinstance(a,int)) or (not(isinstance(b,int))) or (not(b>a))):
            raise ValueError(f"a and b must be of type int. b must be strictly greater than a.")
        range_amount:int = b - a # Range of possible integers
        random_float:float|list[float] = self.random(num_messages=num_messages) 
        if isinstance(random_float,float):
            scaled_float = random_float * range_amount
            base_float = scaled_float + a 
            return math.floor(base_float)
        elif isinstance(random_float,list):
            random_integers:list[int] = []
            for current_random_float in random_float:
                scaled_float = current_random_float * range_amount
                base_float = scaled_float + a 
                random_integers.append(math.floor(base_float))
            return random_integers
    
    def uniform(self, a:float, b:float) -> float:
        """Obtain a provably, verifiably fair random float between a (inclusive) and b (exclusive)"""
        if(not(isinstance(a,(int,float))) or (not(isinstance(b,(int,float)))) or (not(b>a))):
            raise ValueError(f"a and b must be of type int or float. b must be strictly greater than a.")
        range_amount:int = b - a # Range of possible integers
        random_float:float = self.random() 
        scaled_float = random_float * range_amount
        base_float = scaled_float + a 
        return base_float
    
    def shuffle(self, x: MutableSequence[Any]) -> MutableSequence[Any]:
        if not isinstance(x, (list, MutableSequence, Sequence, dict, set, Iterable)):
            raise ValueError(f"x must be a mutable sequence. Got type {type(x)}")
        x = list(x)
        # Fisher-Yates shuffle algorithm
        for i in range(len(x) - 1, 0, -1):
            j = self.randint(0, i + 1)
            if isinstance(j,int):
                x[i], x[j] = x[j], x[i]
        return x
    
    def randrange(self, start: int, stop: int = None, step: int = 1) -> int:
        """Python-compatible randrange implementation"""
        if stop is None:
            stop = start
            start = 0
        
        if step == 1:
            return self.randint(start, stop)
        else:
            # For stepped ranges
            width = stop - start
            if step > 0:
                n = (width + step - 1) // step
            else:
                n = (width + step + 1) // step
            
            if n <= 0:
                raise ValueError("empty range for randrange()")
            
            return start + step * self.randint(0, n)

    def choice(self, seq: MutableSequence[Any]) -> Any:
        """Choose a random element from a non-empty sequence"""
        if not(isinstance(seq,(list,set,dict,tuple,MutableSequence,Sequence,Iterable))):
            raise ValueError(f"Must pass mutable sequence. Got type {type(seq)}")
        if not seq:
            raise ValueError("Cannot choose from an empty sequence")
        return seq[self.randint(0, len(seq))]

    def choices(self, seq:MutableSequence[Any], k=1) -> List[Any]:
        """
        Return a k sized list of elements chosen from the population with replacement.
        
        Args:
            seq: Population to choose from
            k: Number of elements to choose
            
        Returns:
            List of chosen elements
        """
        if not(isinstance(seq,(list,set,dict,tuple,MutableSequence,Sequence,Iterable))):
            raise ValueError(f"Must pass mutable sequence. Got type {type(seq)}")
        if not seq:
            raise ValueError("Cannot choose from an empty sequence")
        if not(isinstance(k,int)):
            raise ValueError("k must be of type int and at least 1.")
        if k<1:
            raise ValueError("Must choose at least 1 element")
        population = list(seq)
        choices_made:list[Any] = []
        for _ in range(k):
            choices_made.append(self.choice(seq=population))
        return choices_made
    
    def sample(self, seq: MutableSequence[Any], k: int) -> List[Any]:
        """Return k unique elements chosen from population without replacement"""
        if k > len(seq):
            raise ValueError("Sample larger than population")
        
        population = list(seq)
        result = []
        
        for i in range(k):
            idx = self.randint(0, len(population))
            result.append(population.pop(idx))
        
        return result

    def generate_new_seed(self,seed_length:int=64) -> str:
        valid_characters = string.digits+string.ascii_lowercase
        return "".join([secrets.choice(valid_characters) for _ in range(seed_length)])

    def new_seeds(self) -> None:
        print(f"CHANGING SEEDS! CURRENT SEEDS --> {self.__str__()}")
        self.key = self.generate_new_seed()
        self.msg = self.generate_new_seed(seed_length=20)
        self.nonce = 1

    def __str__(self) -> str:
        return f"Key: {self.key}\nMessage: {self.msg}\nNonce: {self.nonce}"
    
    def __call__(self):
        return self.random()
    
    def __sizeof__(self):
        return object.__sizeof__(self) + sys.getsizeof(self.key) + sys.getsizeof(self.msg) + sys.getsizeof(self.nonce)

    def __hash__(self) -> int:
        """Hash based on actual state, not string representation"""
        # Create a stable representation of the object's identity
        state_tuple = (self.key, self.msg, self.nonce)
        return hash(state_tuple)

    def __eq__(self, other) -> bool:
        """Proper equality comparison based on state"""
        if not isinstance(other, CryptographicRandom):
            return False
        return (self.key == other.key and 
                self.msg == other.msg and 
                self.nonce == other.nonce)
    
    def __repr__(self):
        return f"Random(key={self.key}, msg={self.msg}, nonce={self.nonce})"