# A Magento 2 module generator library
# Copyright (C) 2016 Derrick Heesbeen
# Copyright (C) 2016 Maikel Martens Changed add API and refactor code
#
# This file is part of Mage2Gen.
#
# Mage2Gen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import os
from .. import Phpclass, Phpmethod, Xmlnode, Snippet, SnippetParam, Readme
try:
    import ujson as json
except:
    import json as json


class PluginSnippet(Snippet):

	description = """Creates a Plugin

	Plugins are designed to overwrite core Magento methods or methods from other 3rd party modules. 

	You can choose to change it before, after, or around the original method is called. 

	Example
	-------

	Change the product name to show pipes before and after the name. 

	Input for the plugin form 

	- **classname:** Magento\Catalog\Model\Product 
	- **methodname:** getName
	- **plugintype:** After

	.. code::
		
		public function afterGetName(
			Magento\Catalog\Model\Product $subject,
			$result
		){
			return '|'.$result.'|';
		}

	"""

	TYPE_BEFORE = 'before'
	TYPE_AFTER = 'after'
	TYPE_AROUND = 'around'

	TYPE_CHOISES = [
		(TYPE_BEFORE, 'Before'),
		(TYPE_AFTER, 'After'),
		(TYPE_AROUND, 'Around'),
	]

	SCOPE_ALL = 'all'
	SCOPE_FRONTEND = 'frontend'
	SCOPE_ADMINHTML = 'backend'
	SCOPE_WEBAPI = 'webapi'
	SCOPE_GRAPHQL = 'graphql'

	SCOPE_CHOISES = [
		(SCOPE_ALL, 'All'),
		(SCOPE_FRONTEND, 'Frontend'),
		(SCOPE_ADMINHTML, 'Backend'),
		(SCOPE_WEBAPI, 'Webapi'),
		(SCOPE_GRAPHQL, 'GraphQl'),
	]

	def get_mage2methods(self):
		with open(os.path.dirname(__file__) + '/mage2methods.json', 'r') as f:
			data = json.load(f)
		return data

	def add(self, classname, methodname, plugintype=TYPE_AFTER, scope=SCOPE_ALL, sortorder=10, disabled=False, extra_params=None):
		# Add class
		plugin_folder = ['Plugin']
		if scope != self.SCOPE_ALL:
			plugin_folder.extend([scope])
		plugin_folder.extend([classname])

		plugin = Phpclass('\\'.join(plugin_folder))
		params = ['\\' + classname + ' $subject']
		returnParams = []
		if plugintype == self.TYPE_AFTER:
			params.append('$result')
		elif plugintype == self.TYPE_AROUND:
			params.append('\Closure $proceed')

		split_classname = classname.split('\\')

		if len(split_classname) > 1:
			try:
				data = self.get_mage2methods()
				parameters = data[methodname][classname]
				if parameters:
					for key, value in parameters.items():
						param = '$' + key
						returnParams.append(param)
						if value != '':
							param += ' = ' + value
						params.append(param)
				else:
					params.append('...$args')
					returnParams.append('...$args')
			except KeyError:
				pass
		else:
			params.append('//$functionParam')

		body = "//Your plugin code"
		if plugintype == self.TYPE_BEFORE:
			body += "\nreturn [" + ', '.join(returnParams) + "];"
		elif plugintype == self.TYPE_AROUND:
			body += "\n$result = $proceed(" + ', '.join(returnParams) + ");"
			body += "\nreturn $result;"
		elif plugintype == self.TYPE_AFTER:
			body += "\nreturn $result;"

		pluginmethodname = plugintype + methodname[0].capitalize() + methodname[1:]
		plugin.add_method(Phpmethod(
			pluginmethodname,
			body=body,
			params=params
		))
	
		# Add plug first will add the module namespace to PhpClass
		self.add_class(plugin)	

		# Plugin XML
		config = Xmlnode('config', attributes={'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance','xsi:noNamespaceSchemaLocation':"urn:magento:framework:ObjectManager/etc/config.xsd"}, nodes=[
			Xmlnode('type', attributes={'name': classname}, nodes=[
				Xmlnode('plugin', attributes={
					'name': plugin.class_namespace.replace('\\', '_'),
					'type':plugin.class_namespace,
					'sortOrder':sortorder,
					'disabled':'true' if disabled else 'false'
				})
			])
		])

		xml_path = ['etc']
		if scope == self.SCOPE_FRONTEND:
			xml_path.append('frontend')
		elif scope == self.SCOPE_ADMINHTML:
			xml_path.append('adminhtml')
		elif scope == self.SCOPE_WEBAPI:
			soap_xml_path = ['etc']
			xml_path.append('webapi_rest')
			soap_xml_path.append('webapi_soap')
			soap_xml_path.append('di.xml')
			self.add_xml(os.path.join(*soap_xml_path), config)
		elif scope == self.SCOPE_GRAPHQL:
			xml_path.append('graphql')

		xml_path.append('di.xml')

		split_classname = classname.split('\\')
		if len(split_classname) > 1:
			etc_module = Xmlnode('config', attributes={
				'xsi:noNamespaceSchemaLocation': "urn:magento:framework:Module/etc/module.xsd"}, nodes=[
				Xmlnode('module', attributes={'name': self.module_name}, nodes=[
					Xmlnode('sequence', attributes={}, nodes=[
						Xmlnode('module', attributes={'name': '{}_{}'.format(split_classname[0], split_classname[1] )})
					])
				])
			])
			self.add_xml('etc/module.xml', etc_module)

		self.add_xml(os.path.join(*xml_path), config)

		self.add_static_file(
			'.',
			Readme(
				specifications=" - Plugin\n\t- {} - {} > {}".format(pluginmethodname, classname, plugin.class_namespace),
			)
		)

	@classmethod
	def params(cls):
		return [
			SnippetParam(name='classname', required=True,
				description='Example: Magento\Catalog\Model\Product',
				regex_validator=r'^[\w\\]+$',
				error_message='Only alphanumeric, underscore and backslash characters are allowed'),
			SnippetParam(name='methodname', required=True,
				description='Example: getPrice',
				regex_validator= r'^\w+$',
				error_message='Only alphanumeric and underscore characters are allowed'),
			SnippetParam(name='plugintype', choises=cls.TYPE_CHOISES, default=cls.TYPE_AFTER),
			SnippetParam(name='scope', choises=cls.SCOPE_CHOISES, default=cls.SCOPE_ALL),
			SnippetParam(name='sortorder', default=10, 
				regex_validator=r'^\d*$', 
				error_message='Must be numeric'),
			SnippetParam(name='disabled', yes_no=True),
		]
		
