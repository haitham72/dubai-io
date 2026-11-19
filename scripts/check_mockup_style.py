with open("design/demo/quest_memory_management_mockup.html", "r", encoding="utf-8") as f:
    text = f.read()

# check where </style> is
pos = text.find("</style>")
print("Position of </style>:", pos)
print("Context around </style>:")
print(text[pos-200:pos+30])
