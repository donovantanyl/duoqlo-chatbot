import firebase_admin
from firebase_admin import credentials, firestore
import datetime
from uuid import uuid4

cred = credentials.Certificate("static/firebase_secret.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def addOutfit(data):
  id = data["id"]
  doc_ref = db.collection('outfits').document(id)
  doc = doc_ref.get()
  if not doc.exists:
      # Create new document
      doc_ref.set(data)
      return True
  return False


def addCatalog(data): # add new clothing
  id = data["id"]
  doc_ref = db.collection('catalog').document(id)
  doc = doc_ref.get()
  if not doc.exists:
      # Create new document
      doc_ref.set(data)
      return True
  return False


def retrieveClothes(category, gender, colour, dresscode):
  # Tones can be defined in colour as well. In this case colour range
  colour_range = [] 

  # Tones include:
  # Neutral: white, black, gray
  # Warm: beige, brown, olive
  # Cool: blue, navy
  
  if colour == "neutral":
    colour_range = ["white","black","gray"]
  elif colour == "warm":
    colour_range = ["beige","brown","olive","wine"]
  elif colour == "cool":
    colour_range = ["blue","navy","green"]
  else:
    # one colour defined
    colour_range = [colour]
  try:
    print(colour_range)
    clothing_list = []
    catalog = db.collection("catalog").stream()
    requirements = {
      "category": category,
      "gender": gender,
      "colours": colour_range,
      "dresscode": dresscode
    }
    for clothing in catalog:
      if len(clothing_list) == 5: # max
        return clothing_list
      clothingdict = clothing.to_dict()
      requirementFail = False
      colourCheck = False # true if it passes requirements
      
      for key, value in requirements.items():
        if str(key) == "colours":
          if value[0] != "":
            for i in colour_range: # Iterate through colour range
              if i in clothingdict[str(key)]:
                colourCheck = True
                break
            if colourCheck == False: #break out of requirement check
              requirementFail = True
              break
        elif str(key) == "gender":
          clothing_gender = clothingdict[str(key)]
          if (clothing_gender != value and value != "") and clothing_gender != "unisex":
            # unisex defaults
            requirementFail = True
            break
        elif str(key) == "category":
          clothing_category = clothingdict[str(key)]
          if clothing_category != value and value != "" and clothing_category != "any":
            # any defaults
            requirementFail = True
            break
        else:
          if clothingdict[str(key)] != value and value != "":
            requirementFail = True
            break
      if requirementFail == False:
        #print(clothingdict)
        clothing_list.append(clothingdict)
    return clothing_list
        
  except Exception as e:
    print(e)
    return []

def checkOutfit(product_id, colour):
  # Check for any outfits that match based on product ID
  # Used for styling suggestions
  
  # Tones can be defined in colour as well. In this case colour range
  colour_range = [] 
  
  # Tones include:
  # Neutral: white, black, gray
  # Warm: beige, brown, olive
  # Cool: blue, navy
  
  if colour == "neutral":
    colour_range = ["white","black","gray"]
  elif colour == "warm":
    colour_range = ["beige","brown","olive","wine"]
  elif colour == "cool":
    colour_range = ["blue","navy","green"]
  else:
    # one colour defined
    colour_range = [colour]
  try:
    outfits = db.collection("outfits").stream()
    for outfit in outfits:
      outfitdict = outfit.to_dict()
      clothing_ids = outfitIDs(outfitdict["id"])
      for i in clothing_ids:
        outfit_colour = outfitdict["clothing_items"][i]["colour"]
        if (product_id == i and outfit_colour in colour_range) or (product_id == i and colour_range[0] == ""):
          # colour_range[0] == "": no preference in colour
          return outfitdict["id"]
    return False # if not found anything
  except Exception as e:
    print(e)
    return False


def outfitIDs(outfit_id):
  # Get clothing IDs of clothes in the outfit
  doc = db.collection("outfits").document(outfit_id).get().to_dict()
  print(doc)
  clothing_items = doc["clothing_items"]
  outfit_list = []
  for key, value in clothing_items.items():
    outfit_list.append(str(key))
  return outfit_list

def trackOrder(order_id):
  try:
    doc_ref = db.collection('orders').document(order_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
    else:
        return doc.to_dict()
  except Exception as e:
    return False

def calculatePrice(product_id, quantity):
  try:
    doc = db.collection("catalog").document(product_id).get().to_dict()
    subtotal = doc["price"] * quantity
    return round(subtotal,2)
  except Exception as e:
    print(e)
    return 0

def clothingName(product_id):
  try:
    doc = db.collection("catalog").document(product_id).get().to_dict()
    return doc["name"]
  except Exception as e:
    return "Not found"

def clothingCategory(product_id):
  try:
    doc = db.collection("catalog").document(product_id).get().to_dict()
    return doc["category"]
  except Exception as e:
    return "Not found"

def checkColour(product_id, colour):
  try:
    doc = db.collection("catalog").document(product_id).get().to_dict()
  except Exception as e:
    return False
  colours = []
  for key, value in doc["colours"].items():
    colours.append(str(key))
  if colour.lower() in colours:
    return doc["colours"][colour.lower()]
  else:
    return False

class Cart:
  def __init__(self, session):
    self.session = session
    doc_ref = db.collection('cart').document(session)
    doc = doc_ref.get()
    if not doc.exists:
        # Create new document
        data = {
          "cart_items":[],
          "last_updated": datetime.datetime.now(tz=datetime.timezone.utc)
        }
        doc_ref.set(data)

  def add_cart(self, cart_items):
    cart_dict = self.get_dict()
    original_cart_items = cart_dict["cart_items"]

    # Check if already exists, if it does then +1 to quantity
    for i in cart_items:
      item_exists = False
      for j in original_cart_items:
        if i["colour"] == j["colour"] and i["product_id"] == j["product_id"] and i["sizing"] == j["sizing"]:
          j["quantity"] += i["quantity"]
          item_exists = True
          break
      if not item_exists:
        original_cart_items.append(i)
    data = {
      "cart_items":original_cart_items,
      "last_updated": datetime.datetime.now(tz=datetime.timezone.utc)
    }
    try:
      doc_ref = db.collection('cart').document(self.session)
      doc_ref.set(data)
    except Exception as e:
      print(e)
      return False
    else:
      return True


  def remove_cart(self, product_id, colour, sizing):
    cart_dict = self.get_dict()
    original_cart_items = cart_dict["cart_items"]
    old_length = len(original_cart_items)
    # Check if already exists, if it does then remove
    for i in range(len(original_cart_items)):
      cart_item = original_cart_items[i]
      if cart_item["product_id"] == product_id and cart_item["colour"] == colour and cart_item["sizing"] == sizing:
        del original_cart_items[i]
        break
    data = {
      "cart_items":original_cart_items,
      "last_updated": datetime.datetime.now(tz=datetime.timezone.utc)
    }
    try:
      doc_ref = db.collection('cart').document(self.session)
      doc_ref.set(data)
    except Exception as e:
      print(e)
      return False
    else:
      return old_length != len(original_cart_items) # Returns false if wasnt deleted


  def checkout(self, session):
    db.collection("cart").document(session).delete()
    orderid = str(uuid4())
    data = {
      "orderdate": datetime.datetime.now(tz=datetime.timezone.utc),
      "orderid": orderid,
      "orderstatus": "Processing"
    }
    db.collection("orders").document(orderid).set(data)
    return orderid
      
  
  def get_dict(self):
    doc_ref = db.collection('cart').document(self.session)
    doc = doc_ref.get()
    # Update in case of any changes
    cartdict = doc.to_dict()
    return cartdict

    
  

class Clothing:
  def __init__(self, product_id):
    self.product_id = str(product_id)
    doc = db.collection("catalog").document(self.product_id).get()
    self.clothingdict = doc.to_dict()
    # query firestore to get the dictionary

  def get_dict(self):
    return self.clothingdict

  def get_colours(self):
    colours = []
    for key, value in self.clothingdict["colours"].items():
      colours.append(str(key))
    return colours

  def check_colour(self, colour): # check if colour exists
    colours = self.get_colours()
    if colour.lower() in colours:
      return self.clothingdict["colours"][colour.lower()]
    else:
      return False


class Outfit:
  def __init__(self, outfit_id):
    self.outfit_id = str(outfit_id)
    doc = db.collection("outfits").document(self.outfit_id).get()
    self.outfitdict = doc.to_dict()

  def get_dict(self):
    return self.outfitdict

  def get_ids(self):
    # Get clothing IDs of clothes in the outfit
    outfit_list = []
    for key, value in self.outfitdict["clothing_items"]:
      outfit_list.append(str(key))
    return outfit_list

  def check_clothing(self, product_id):
    # Check if the provided product id is inside this outfit
    outfit_list = self.get_ids()
    if str(product_id) in outfit_list:
      return self.outfitdict["clothing_items"][str(product_id)]
    else:
      return False

