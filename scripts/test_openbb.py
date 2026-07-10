from openbb import obb

print(type(obb))
print()

print("Has equity:", hasattr(obb, "equity"))
print("Has forex:", hasattr(obb, "forex"))
print("Has currency:", hasattr(obb, "currency"))
print("Has price:", hasattr(obb, "price"))

print()

print(dir(obb))