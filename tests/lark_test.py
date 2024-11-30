from eldar import Index

documents = [
    "La mejor hamburguesa con queso está en oferta dos por uno",
    "Descuento en sándwich vegano",
    "Hamburguesa de pollo sin champiñones",
    "Oferta especial de dos por uno en hamburguesas y sándwiches",
    "No hay descuento en la hamburguesa vegana",
    "Sándwich vegetariano con aguacate y tomate",
    "Hamburguesa de tofu con champiñones y cebolla caramelizada",
    "Sándwich de jamón y queso dos por uno",
]

index = Index()
index.build(documents)

consulta = (
    '(hamburguesa OR sándwich) /7 (descuento OR "dos por uno") -vegana -vegetariana'
)

resultados = index.search(consulta)

print(resultados)
