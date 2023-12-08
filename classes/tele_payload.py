import json
import requests
from classes.firestore import outfitIDs, clothingName, clothingCategory

class ClothingCard:
  # Create card rich response element to be sent in chatbot
  def __init__(self, clothing):
    self.clothing = clothing
    self.buttons = []
    self.title = "title"
    self.subtitle = ""
    self.imageUri = ""

    if clothing:
      colours = ""
      for key, value in clothing["colours"].items():
        colours = colours + str(key) + ", "
      colours = colours[:len(colours)-2]
      self.title = "{} \n(PID: {}) \nS${:.2f}".format(clothing["name"], clothing["id"], clothing["price"])
      self.subtitle = "{} \n\nColours available: {}".format(clothing["description"], colours)
      self.imageUri = clothing["icon"]

  def add_button(self, buttonName, postback):
    newButton = {
      "text": buttonName,
      "postback": postback
    }
    self.buttons.append(newButton)

  def set_image(self, imageUri):
    self.imageUri = imageUri
    return self.imageUri

  def get_content(self):
      return {
        "title": self.title,
        "subtitle": self.subtitle,
        "imageUri": self.imageUri,
        "buttons": self.buttons
      }


class OutfitCard:
  # Create outfit card rich response element to be sent in chatbot
  def __init__(self, outfit):
    self.outfit = outfit
    self.buttons = []
    self.title = "title"
    self.subtitle = ""
    self.imageUri = ""

    if outfit:
      clothing_ids = outfitIDs(outfit["id"])
      self.title = "{} {} OUTFIT".format(outfit["dresscode"].upper(), outfit["gender"].upper())
      subtitleText = "Model height: {}".format(outfit["height"])
      for i in range(len(clothing_ids)):
        id = clothing_ids[i]
        clothing_name = clothingName(id)
        colour = outfit["clothing_items"][id]["colour"]
        sizing = outfit["clothing_items"][id]["sizing"]
        clothing_category = clothingCategory(id)
        subtitleText += "\n\n#{} ({}): {} {} \nSize: {} (PID: {})".format(i+1, clothing_category.upper(), colour.upper(), clothing_name, sizing, id)
        newButton = {
          "text": "View #{}'s info".format(i+1),
          "postback": "show me info about {} {}".format(colour.upper(), clothing_name)
        }
        self.buttons.append(newButton)
      self.subtitle = subtitleText
      self.imageUri = outfit["icon"]

  def add_button(self, buttonName, postback):
    newButton = {
      "text": buttonName,
      "postback": postback
    }
    self.buttons.append(newButton)

  def set_image(self, imageUri):
    self.imageUri = imageUri
    return self.imageUri

  def get_content(self):
    return {
      "title": self.title,
      "subtitle": self.subtitle,
      "imageUri": self.imageUri,
      "buttons": self.buttons
    }

