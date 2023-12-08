from flask import Flask, request
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from classes.tele_payload import ClothingCard, OutfitCard
from classes.firestore import Clothing, Cart, Outfit
from classes.firestore import calculatePrice, clothingName, checkColour, trackOrder, checkOutfit, retrieveClothes
import datetime
from classes.firestore import addOutfit, addCatalog
#from classes.tele_payload import send_multiple_images


#cred = credentials.Certificate("static/firebase_secret.json")
#firebase_admin.initialize_app(cred)
#db = firestore.client()

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello from Flask!'

# add webhook security whenever free
@app.route('/webhook', methods=['POST'])
def webhook():
  exceptionReturn = {
      "fulfillmentText": "Sorry, there was an error in processing your request. Please try again.",
      "source": 'webhook'
  }
  
  req = request.get_json(silent=True, force=True)
  session = req.get('session')
  query_result = req.get('queryResult')
  intent = query_result.get('intent').get('displayName')
  print(session)
  print(intent)

  if intent == "webhook.test":
    return {
        "fulfillmentText": "✅ Webhook response",
        "source": 'webhook'
    }

  
  elif intent == "outfit.new":
    try:
      dresscode = query_result.get('parameters').get('dresscode')
      gender = query_result.get('parameters').get('gender')
    except Exception as e:
      print(e)
      return exceptionReturn
    else:
      print(dresscode)
      print(gender)
      if dresscode == "formal":
        if gender == "men":
          outfit = Outfit("formalmen1").get_dict()
        elif gender == "women":
          outfit = Outfit("formalwomen1").get_dict()
        else:
          outfit = Outfit("formalmen2").get_dict
      else: # Dresscode casual
        if gender == "women":
          outfit = Outfit("casualwomen1").get_dict()
        else:
          outfit = Outfit("casualmen1").get_dict()
      outfitCard = OutfitCard(outfit)
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "Found an outfit for you!"
              ]
            }
          },
          {
            "card": outfitCard.get_content()
          },
        ]
      }


  elif intent == "outfit.styling":
    try:
      product_id = query_result.get('parameters').get('clothing')
      colour = query_result.get('parameters').get('colour')
      print("Styling options for")
      print(product_id)
      print(colour)
    except Exception as e:
      print (e)
      return exceptionReturn
    outfit_found = checkOutfit(product_id, colour)
    if outfit_found:
      outfit = Outfit(outfit_found).get_dict()
      outfitCard = OutfitCard(outfit)
      text_output = "Here's an outfit that I could find to match your"
      if colour == "":
        text_output += " {}:".format(clothingName(product_id))
      else:
        # Colour wasnt blank
        text_output += " {} {}:".format(colour.upper(), clothingName(product_id))
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                text_output
              ]
            }
          },
          {
            "card": outfitCard.get_content()
          },
        ]
      }
    else:
      # No outfit was found
      return {
        "fulfillmentMessages": [
          {
            "card": {
              "title": "Sorry, we do not have any outfit ideas with this specific clothing item for you at the moment.\n\nWant to find another look?",
              "buttons": [
                {
                  "text": "👔👗 Find a new look",
                  "postback": "i'm looking for a new outfit"
                }
              ]
            }
          },
        ],
      }


  elif intent == "clothing.discover":
    try:
      category = query_result.get('parameters').get('category')
      gender = query_result.get('parameters').get('gender')
      colour = query_result.get('parameters').get('colour')
      colourtone = query_result.get('parameters').get('colourtone')
      dresscode = query_result.get('parameters').get('dresscode')
      print(colour)
      print(colourtone)
      print(category)
    except Exception as e:
      print(e)
      return exceptionReturn
    colour_range = "" #Used for final filtering
    if colourtone and not colour: # Colour tone provided but no specific colour
      colour_range = colourtone
    elif colour: # Colour specified
      colour_range = colour

    print(colour_range)
    clothing_list = retrieveClothes(category, gender, colour_range, dresscode)
    #print("discovering clothes")
    #print(clothing_list)
    if len(clothing_list) > 0:
      output_text = "🔍 Found some clothes that match!\n"
      button_list = []
      #optional to include thumbnail
      imageUri = clothing_list[0]["icon"]
      for i in range(len(clothing_list)):
        clothing = clothing_list[i]
        clothing_name = clothing["name"]
        id = clothing["id"]
        output_text += "\n#{}: {} (PID: {})".format(i+1, clothing_name, id)
        button_text = {
          "text": "View #{}'s info".format(i+1),
          "postback": "show me {} info".format(clothing_name)
        }
        button_list.append(button_text)
      return {
        "fulfillmentMessages": [
          {
            "card": {
              "title": output_text,
              #"imageUri": imageUri,
              "buttons": button_list
            }
          },
        ],
      }
    else:
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "Sorry, we did not manage to find any clothing that matches your query."
              ]
            }
          },
        ]
      }

  elif intent == "clothing.info" or intent == "clothing.info - colour":
    try:
      product_id = query_result.get('parameters').get('clothing')
      colour = query_result.get('parameters').get('colour')
    except Exception as e:
      print(e)
      return exceptionReturn
    clothing = Clothing(product_id).get_dict()
    clothingcard = ClothingCard(clothing)

    if intent == "clothing.info - colour" and colour == "": # Show multiple selection for colour
      colour_list = []
      button_list = []
      for key, value in clothing["colours"].items():
        colour_list.append(str(key))
      for i in colour_list:
        button_text = {
          "text": i.capitalize(),
          "postback": i
        }
        button_list.append(button_text)
      return {
        "fulfillmentMessages": [
          {
            "card": {
              "title": "What colour would you like to see?",
              "buttons": button_list
            }
          },
        ]
      }
    
    # Proceed with regular intent if not specifically colour
    prompttext = ""
    final_colour = ""
    if colour != "": # colour field was not left blank
      clothing_colour = checkColour(product_id, colour)
      print(colour, clothing_colour)
      if clothing_colour == False: # COLOUR GIVEN BUT NOT AVAILABLE
        prompttext += "Unfortunately, {} is not one of the available colours. ".format(colour, clothing["name"])
        clothingcard.add_button("Add to cart","i want to add {} to my cart".format(clothing["id"]))
        clothingcard.add_button("View other colours","i want to see colours of {}".format(clothing["name"]))
      
      else:
        clothingcard.set_image(clothing_colour)
        # Set colour based
        final_colour = colour
        clothingcard.add_button("Add colour to cart","i want to add {} {} to my cart".format(colour, clothing["id"]))
        clothingcard.add_button("View other colours","i want to see colours of {}".format(clothing["name"]))
        
    else: # No colour field
      clothingcard.add_button("Add to cart","i want to add {} to my cart".format(clothing["id"]))
      clothingcard.add_button("View colours","i want to see colours of {}".format(clothing["name"]))
    
    prompttext += "\n\nHere's some info about {}:".format(clothing["name"])
    return {
      "fulfillmentMessages": [
        {
          "text": {
            "text": [
              prompttext
            ]
          }
        },
        {
          "card": clothingcard.get_content()
        }
      ],
      "outputContexts": [
        {
          "name": "{}/contexts/clothinginfo-followup".format(session),
          "lifespanCount": 2,
          "parameters": {
            "clothing": clothing["id"],
            "colour": final_colour,
          }
        }
      ],
    }
  
  elif intent == "cart.view":
    cart = Cart(session)
    cartdict = cart.get_dict()
    cart_items = cartdict["cart_items"]
    if len(cart_items) == 0:
      return {
        "fulfillmentMessages": [
          {
            "card": {
              "title": "🛒 There's nothing in your cart at the moment, want to go do some shopping?",
              "buttons": [
                {
                  "text": "👔👗 Find a new look",
                  "postback": "i'm looking for a new outfit"
                }
              ]
            }
          },
        ],
      }
    else:
      # Text formatting
      cart_string = ""
      #print(cartdict)
      totalprice = 0
      for i in range(len(cart_items)):
        clothing = cart_items[i]
        id = clothing["product_id"]
        quantity = clothing["quantity"]
        sizing = clothing["sizing"]
        colour = clothing["colour"].upper()
        subtotal = calculatePrice(id,quantity)
        totalprice += subtotal
        cart_string += "{}: {} {}\n(PID: {}) Quantity: {} Size: {}\nSubtotal: S${:.2f}\n\n ".format(i+1, colour, clothingName(id), id, quantity, sizing, subtotal)
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "🛒 Here's your current cart: \n{}Total Price: S${:.2f}".format(cart_string, totalprice)
              ]
            }
          },
        ]
      }
  
  elif intent == "cart.add":
    #print(query_result)
    try:
      product_id = query_result.get('parameters').get('clothing')
      quantity = int(query_result.get('parameters').get('quantity'))
      sizing = query_result.get('parameters').get('sizing')
      colour = query_result.get('parameters').get('colour')
    except Exception as e:
      print(e)
      return exceptionReturn
    else:
      if not product_id:
        return {
            "fulfillmentText": "What product would you like to add to the cart?",
            "source": 'webhook'
        }
      clothingObj = Clothing(product_id)
      clothing = clothingObj.get_dict()
      if not sizing:
        return {
            "fulfillmentText": "What size for {}?\n\nAvailable sizes: XS, S, M, L, XL, 2XL, 3XL".format(clothing["name"]),
            "source": 'webhook'
        }
      if not colour:
        colour_text = ""
        for i in clothingObj.get_colours():
          colour_text += "{}, ".format(i)
        return {
            "fulfillmentText": "What colour for {}?\n\nAvailable colours: {}".format(clothing["name"],colour_text[:len(colour_text)-2]),
            "source": 'webhook'
        }
      if not checkColour(product_id, colour):
        colours = ""
        for key, value in clothing["colours"].items():
          colours = colours + str(key) + ", "
        colours = colours[:len(colours)-2]
        return {
          "fulfillmentMessages": [
            {
              "text": {
                "text": [
                  "That is not a valid colour! \nWhat colour for {}? \nOptions: {}".format(clothing["name"], colours)
                ]
              }
            }
          ]
        }
      #print("test")
      cart_items = [{"colour":colour,"product_id":product_id,"quantity":quantity,"sizing":sizing}]
      # Add to cart
      cart = Cart(session)
      cart.add_cart(cart_items)
      #print(cart.get_dict())
      return {
          "fulfillmentText": "✅ Added x{} {} {} (SIZE {}) to cart! Would you like to add another item?".format(quantity, colour.upper(), clothing["name"], sizing),
          "source": 'webhook'
      }


  elif intent == "cart.remove":
    #print(query_result)
    try:
      product_id = query_result.get('parameters').get('clothing')
      colour = query_result.get('parameters').get('colour')
      sizing = query_result.get('parameters').get('sizing')
    except Exception as e:
      print(e)
      return exceptionReturn
    else:
      print("cart intent went thru")
      # Add to cart
      cart = Cart(session)
      removeCheck = cart.remove_cart(product_id, colour, sizing)
      #print(cart.get_dict())
      if removeCheck == True:
        return {
            "fulfillmentText": "✅ Successfully removed {} {} (SIZE {}) from cart!".format(colour.upper(), clothingName(product_id), sizing),
            "source": 'webhook'
        }
      else:
        return {
            "fulfillmentText": "I did not find a {} {} (SIZE {}) in your cart.".format(colour.upper(), clothingName(product_id), sizing),
            "source": 'webhook'
        }


  elif intent == "cart.checkout":
    cart = Cart(session)
    cartdict = cart.get_dict()
    cart_items = cartdict["cart_items"]
    if len(cart_items) == 0:
      return {
        "fulfillmentMessages": [
          {
            "card": {
              "title": "🛒 There's nothing in your cart at the moment, want to go do some shopping?",
              "buttons": [
                {
                  "text": "👔👗 Find a new look",
                  "postback": "i'm looking for a new outfit"
                }
              ]
            }
          },
        ],
      }
    else:
      # Text formatting
      cart_string = ""
      print(cartdict)
      totalprice = 0
      for i in range(len(cart_items)):
        clothing = cart_items[i]
        id = clothing["product_id"]
        quantity = clothing["quantity"]
        sizing = clothing["sizing"]
        colour = clothing["colour"].upper()
        subtotal = calculatePrice(id,quantity)
        totalprice += subtotal
        cart_string += "{}: {} {}\n(PID: {}) Quantity: {} Size: {}\nSubtotal: S${:.2f}\n\n ".format(i+1, colour, clothingName(id), id, quantity, sizing, subtotal)
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "🛒 Here's your current cart: \n{}Total Price: S${:.2f}".format(cart_string, totalprice)
              ]
            }
          },
          {
            "card": {
              "title": "Are you sure you're ready to check out?",
              "buttons": [
                {
                  "text": "Pay & Check-out",
                  "postback": "yes"
                },
                {
                  "text": "Continue shopping",
                  "postback": "no"
                }
              ]
            }
          },
        ]
      }


  elif intent == "cart.checkout - yes":
    cart = Cart(session)
    checkoutCart = cart.checkout(session)
    if checkoutCart != False:
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "📦 New order was successfully created! Take note of this order ID for order tracking: `{}` \n\nThank you for shopping at DUOQLO! Have a nice day!".format(checkoutCart)
              ]
            }
          },
        ]
      }
    else:
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "Unfortunately, there was an error with completing your order."
              ]
            }
          },
        ]
      }


  elif intent == "order.track":
    try:
      order_id = query_result.get('parameters').get('order')
    except Exception as e:
      print(e)
      return exceptionReturn
    order = trackOrder(order_id)
    if order == False:
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "Sorry, the order ID was not found. Please re-check that you've entered it correctly."
              ]
            }
          },
        ]
      }
    else:
      return {
        "fulfillmentMessages": [
          {
            "text": {
              "text": [
                "Order found!"
              ]
            }
          },
          {
            "card": {
              "title": "📦 Order ID ({}):\n\n".format(order_id),
              "subtitle": "Order Date: {}\nOrder Status: {}".format(order["orderdate"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"), order["orderstatus"]),
              "buttons": [
                {
                  "text": "Track another order",
                  "postback": "i want to track an order"
                },
              ]
            }
          },
        ]
      }
  
  
  else:
    return("Test")


app.run(host='0.0.0.0', port=81)
