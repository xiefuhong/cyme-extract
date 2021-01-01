#!/usr/bin/python3
import sys
import glob
import datetime as dt
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from math import sqrt

#
# Load user configuration ()
#
config = pd.DataFrame({
	"GLM_NOMINAL_VOLTAGE" : ["4.16 kV"],
	"GLM_INCLUDE" : [""],
	"GLM_DEFINE" : [""],
	}).transpose().set_axis(["value"],axis=1,inplace=0)
config.index.name = "name" 
try:
	settings = pd.read_csv("../config.csv", dtype=str,
		names=["name","value"],
		comment = "#",
		).set_index("name")
	for name, values in settings.iterrows():
		if name in config.index:
			config["value"][name] = values[0]
except:
	pass
settings = config["value"]
print(f"Running write_glm.py:")
for name, data in config.iterrows():
	print(f"  {name} = {data['value']}")
del config

#
# Load all the model tables (table names have an "s" appended)
#
for filename in glob.iglob("*.csv"):
	data = pd.read_csv(filename, dtype=str)
	name = filename[0:-4]
	index = data.columns[0]
	globals()[name+"s"] = data.set_index(index)

#
# GLM file builder
#
class GLM:

	def __init__(self,file,mode):

		self.fh = open(file,mode)
		self.objects = {}

	def __del__(self):
		self.close()

	def write(self,line):
		print(line,file=self.fh)

	def blank(self):
		self.write("")

	def comment(self,lines):
		if type(lines) is list:
			for line in lines:
				self.write(f"// {line}")
		else:
			self.write(f"// {lines}")

	def set(self,name,value):
		self.write(f"#set {name}={value}")

	def define(self,name,value):
		self.write(f"#define {name}={value}")

	def include(self,name,brackets="\"\""):
		self.write(f"#include {brackets[0]}{name}{brackets[1]}")

	def module(self, name, parameters = {}):
		if not parameters:
			self.write(f"module {name};")
		else:
			self.write(f"module {name}")
			self.write("{")
			for tag, value in parameters.items():
					if type(value) is str:
						self.write(f"\t{tag} \"{value}\";")
					else:
						self.write(f"\t{tag} {value};")
			self.write("}")

	def object(self, oclass, name, parameters):
		if name not in self.objects.keys():
			obj = {"name" : name}
			self.objects[name] = obj
		else:
			obj = self.objects[name]
		for tag,value in parameters.items():
			obj[tag] = value
		obj["class"] = oclass
		return obj

	def close(self):
		for name, parameters in self.objects.items():
			self.write(f"object {parameters['class']}")
			self.write("{")
			for tag, value in parameters.items():
				if tag != "class":
					if type(value) is str:
						self.write(f"\t{tag} \"{value}\";")
					else:
						self.write(f"\t{tag} {value};")
			self.write("}")
		self.objects = {}

	def name(self,name,oclass=None):
		if oclass:
			return oclass + "_" + name
		elif "0" <= name[0] <= "9":
			return "_"+name
		else:
			return name
#
# Phase mapping
#
cyme_phase_name = { 1:"A", 2:"B", 3:"C", 4:"AB", 5:"AC", 6:"BC", 7:"ABC"} # CYME phase number -> phase names
glm_phase_code = {"A":1, "B":2, "C":4, "AB":3, "AC":5, "BC":6, "ABC":7} # GLM phase name -> phase number
glm_phase_name = {1:"A",2:"B",3:"AB",4:"C",5:"AC",6:"BC",7:"ABC"} # GLM phase number -> phase name

#
# Device mapping
#
cyme_devices = {
	1 : "UndergroundLine",
	2 : "OverheadLine",
	3 : "OverheadByPhase",
	4 : "Regulator",
	5 : "Transformer",
	6 : "Not used",
	7 : "Not used",
	8 : "Breaker",
	9 : "LVCB",
	10 : "Recloser",
	11 : "Not used",
	12 : "Sectionalizer",
	13 : "Switch",
	14 : "Fuse",
	15 : "SeriesCapacitor",
	16 : "SeriesReactor",
	17 : "ShuntCapacitor",
	18 : "ShuntReactor",
	19 : "Not used",
	20 : "SpotLoad",
	21 : "DistributedLoad",
	22 : "Miscellaneous",
	23 : "OverheadLineUnbalanced",
	24 : "ArcFurnace",
	25 : "CTypeFilter",
	26 : "DoubleTunedFilter",
	27 : "HighPassFilter",
	28 : "IdealConverter",
	29 : "NonIdealConverter",
	30 : "ShuntFrequencySource",
	31 : "Not used",
	32 : "SingleTunedFilter",
	33 : "InductionMotor",
	34 : "SynchronousMotor",
	35 : "InductionGenerator",
	36 : "SynchronousGenerator",
	37 : "ElectronicConverterGenerator",
	38 : "TransformerByPhase",
	39 : "ThreeWindingTransformer",
	40 : "NetworkEquivalent",
	41 : "Wecs",
	42 : "GroundingTransformer",
	43 : "MicroTurbine",
	44 : "Sofc",
	45 : "Photovoltaic",
	46 : "SeriesFrequencySource",
	47 : "AutoTransformer",
	48 : "ThreeWindingAutoTransformer",
}
glm_devices = {
	1 : "underground_line",
	2 : "overhead_line",
	3 : "overhead_line",
	4 : "regulator",
	5 : "transformer",
	8 : "breaker",
	10 : "recloser",
	12 : "sectionalizer",
	13 : "switch",
	14 : "fuse",
	17 : "capacitor",
	20 : "load",
	23 : "load",
}

#
# Process each network
#
def table_find(table,**kwargs):
	result = table
	for key,value in kwargs.items():
		result = result[result[key]==value]
	return result

def table_get(table,id,range=0):
	return table.loc[id][range]

for network_id, network in networks.iterrows():
	
	version = network["Version"]
	creation_time = int(network["CreationTime"])
	last_change = int(network["LastChange"])
	load_factor = float(network["LoadFactor"])
	head_node = table_get(headnodes,network_id)

	glm = GLM(f"../network_{network_id}.glm","w")
	glm.comment([
		f"Automatically generated by https://github.com/openfido/cyme_extract/postproc/write_glm.py",
		f"Generated on {dt.datetime.utcnow()} UTC",
		f"",
		f"CYME version: {version}",
		f"CYME creation time: {dt.datetime.fromtimestamp(creation_time)}",
		f"CYME last change: {dt.datetime.fromtimestamp(last_change)}",
		f"",
		])

	# settings from model
	glm.blank()
	glm.define("CYME_LOADFACTOR",load_factor)
	glm.define("CYME_NETWORKID",network_id)

	# settings from config.csv
	for include in settings["GLM_INCLUDE"].split():
		glm.include(include.strip())
	define = settings["GLM_DEFINE"].split("=")
	glm.define(define[0].strip(),define[1].strip())

	glm.blank()
	glm.comment(["","Modules",""])
	glm.module("powerflow",{"solver_method":"NR"})

	node_dict = {}
	device_dict = {}
	node_links = {}

	# nodes graph data
	for node_id, node in table_find(nodes,NetworkId=network_id).iterrows():
		node_links[node_id] = [] # incident links
		node_dict[node_id] = [] # node dictionary

	glm.blank()
	glm.comment(["","Objects",""])

	# links
	for section_id, section in table_find(sections,NetworkId=network_id).iterrows():
		phase = int(section["Phase"])
		from_node_id = section["FromNodeId"]
		to_node_id = section["ToNodeId"]
		for device_id, device in table_find(sectiondevices,SectionId=section_id).iterrows():
			device_type = int(device["DeviceType"])
			if device_type in glm_devices.keys():
				device_name = glm.name(device_id,"link")
				device_dict[device_id] = glm.object("link", device_name , {
					"phases" : cyme_phase_name[phase],
					"nominal_voltage" : settings["GLM_NOMINAL_VOLTAGE"],
					"from" : glm.name(from_node_id,"node"),
					"to" : glm.name(to_node_id,"node"),
					})
				node_links[from_node_id].append(device_id)
				node_links[to_node_id].append(device_id)
			else:
				print("*** WARNING ***")
				print(f"  Network {network_id} device {device_id}: device type {device_type} ({cyme_devices[device_type]}) has no corresponding GLM object")
				print(f"  Omitting device {device_id} is likely to change the results and/or cause solver issues")

	# nodes
	for node_id in node_dict.keys():
		phase = 0
		for device_id in node_links[node_id]:
			phase |= glm_phase_code[device_dict[device_id]["phases"]]
		obj = glm.object("node", glm.name(node_id,"node"), {
			"phases" : glm_phase_name[phase],
			"nominal_voltage":settings["GLM_NOMINAL_VOLTAGE"],
			})
		if node_id == head_node:
			obj["bustype"] = "SWING"
		else:
			obj["bustype"] = "PQ"
		node_dict[node_id] = obj

	# 3phase overhead lines
	def add_overhead_line_conductors(conductors):
		names = []
		for conductor_id in conductors:
			conductor_name = glm.name(conductor_id,"overhead_line_conductor")
			if not conductor_name in glm.objects.keys():
				conductor = eqconductors.loc[conductor_id]
				gmr = float(conductor["GMR"])
				r25 = float(conductor["R25"])
				diameter = float(conductor["Diameter"])
				nominal_rating = float(conductor["NominalRating"])
				obj = glm.object("overhead_line_conductor",conductor_name,{
					"geometric_mean_radius" : "%.2f cm" % gmr,
					"resistance" : "%.5f Ohm/km" % r25,
					"diameter" : "%.2f cm" % diameter,
					"rating.summer.continuous" : "%.1f A" % nominal_rating,
					"rating.winter.continuous" : "%.1f A" % nominal_rating,
					"rating.summer.emergency" : "%.1f A" % nominal_rating,
					"rating.winter.emergency" : "%.1f A" % nominal_rating,
					})
			names.append(conductor_name)
		return names

	def add_line_spacing(spacing_id):
		spacing_name = glm.name(spacing_id,"line_spacing")
		if not spacing_name in glm.objects.keys():
			spacing = eqgeometricalarrangements.loc[spacing_id]
			Ax = float(spacing["ConductorA_Horizontal"])
			Ay = float(spacing["ConductorA_Vertical"])
			Bx = float(spacing["ConductorA_Horizontal"])
			By = float(spacing["ConductorA_Vertical"])
			Cx = float(spacing["ConductorA_Horizontal"])
			Cy = float(spacing["ConductorA_Vertical"])
			Nx = float(spacing["NeutralConductor_Horizontal"])
			Ny = float(spacing["NeutralConductor_Vertical"])
			ABx = Ax-Bx; ABy = Ay-By
			ACx = Ax-Cx; ACy = Ay-Cy
			BCx = Bx-Cx; BCy = By-Cy
			ANx = Ax-Nx; ANy = Ay-Ny
			BNx = Bx-Nx; BNy = By-Ny
			CNx = Cx-Nx; CNy = Cy-Ny
			glm.object("line_spacing",spacing_name,{
				"distance_AB" : "%.2f m"%sqrt(ABx*ABx+ABy*ABy),
				"distance_AC" : "%.2f m"%sqrt(ACx*ACx+ACy*ACy),
				"distance_BC" : "%.2f m"%sqrt(BCx*BCx+BCy*BCy),
				"distance_AN" : "%.2f m"%sqrt(ANx*ANx+ANy*ANy),
				"distance_BN" : "%.2f m"%sqrt(BNx*BNx+BNy*BNy),
				"distance_CN" : "%.2f m"%sqrt(CNx*CNx+CNy*CNy),
				"distance_AE" : "%.2f m"%Ay,
				"distance_BE" : "%.2f m"%By,
				"distance_CE" : "%.2f m"%Cy,
				"distance_NE" : "%.2f m"%Ny,
				})
		return spacing_name

	def add_line_configuration(items):
		configuration_id = "_".join(items)
		configuration_name = glm.name(configuration_id,"line_configuration")
		if not configuration_name in glm.objects.keys():
			glm.object("line_configuration",configuration_name,{
				"conductor_A" : glm.name(items[0],"overhead_line_conductor"),
				"conductor_B" : glm.name(items[1],"overhead_line_conductor"),
				"conductor_C" : glm.name(items[2],"overhead_line_conductor"),
				"conductor_N" : glm.name(items[3],"overhead_line_conductor"),
				"spacing" : glm.name(items[4],"line_spacing")
				})
		return configuration_name

	for line_id, line in table_find(overheadbyphases,NetworkId=network_id).iterrows():
		line_name = glm.name(line_id,"link")
		length = float(line["Length"])
		conductorA_id = line["PhaseConductorIdA"]
		conductorB_id = line["PhaseConductorIdB"]
		conductorC_id = line["PhaseConductorIdC"]
		conductorN_id = line["NeutralConductorId"]
		add_overhead_line_conductors([conductorA_id,conductorB_id,conductorC_id,conductorN_id])
		spacing_id = line["ConductorSpacingId"]
		add_line_spacing(spacing_id)
		configuration_name = add_line_configuration([conductorA_id,conductorB_id,conductorC_id,conductorN_id,spacing_id])
		glm.object("overhead_line", line_name, {
			"length" : "%.2f m"%length,
			"configuration" : configuration_name,
			})


	# unbalanced overhead lines
	for line_id, line in table_find(overheadlineunbalanceds,NetworkId=network_id).iterrows():
		line_name = glm.name(line_id,"link")
		configuration_id = line["LineId"]
		configuration_name = glm.name(configuration_id,"line_configuration")
		length = float(line["Length"])
		glm.object("overhead_line", line_name, {
			"length" : "%.2f m"%length,
			"configuration" : configuration_name,
			})
		if not configuration_name in glm.objects.keys():
			configuration = eqoverheadlineunbalanceds.loc[configuration_id]
			conductorA_id = configuration["PhaseConductorIdA"]
			conductorB_id = configuration["PhaseConductorIdB"]
			conductorC_id = configuration["PhaseConductorIdC"]
			conductorN_id = configuration["NeutralConductorId"]
			conductor_names = add_overhead_line_conductors([conductorA_id,conductorB_id,conductorC_id,conductorN_id])
			spacing_id = configuration["ConductorSpacingId"]
			spacing_name = add_line_spacing(spacing_id)
			glm.object("line_configuration",configuration_name,{
				"conductor_A" : conductor_names[0],
				"conductor_B" : conductor_names[1],
				"conductor_C" : conductor_names[2],
				"conductor_N" : conductor_names[3],
				"spacing" : spacing_name,
				})

	# switches
	def phase_state(phases,state):
		if state in phases:
			return "CLOSED"
		else:
			return "OPEN"
	for switch_id, switch in table_find(switchs,NetworkId=network_id).iterrows():
		switch_name = glm.name(switch_id,"link")
		phases = cyme_phase_name[int(switch["ClosedPhase"])]
		glm.object("switch", switch_name, {
			"phase_A_state" : phase_state(phases,"A"),
			"phase_B_state" : phase_state(phases,"B"),
			"phase_C_state" : phase_state(phases,"C"),
			"operating_mode" : "BANKED"
			})

	glm.close()


