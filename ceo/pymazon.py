#!/usr/bin/python

from xml.dom import minidom, Node
import urllib
import time

class PyMazonError(Exception):
	"""Holds information about an error that occured during a pymazon request"""
	def __init__(self, messages):
		self.__message = '\n'.join(messages)

	def __get_message(self):
		return self.__message

	def __str__(self):
		return repr(self.__message)

	message = property(fget=__get_message)


class PyMazonBook:
	"""Stores information about a book retrieved via PyMazon."""
	def __init__(self, title, authors, publisher, year, isbn10, isbn13, edition):
		self.__title = title
		self.__authors = authors
		self.__publisher = publisher
		self.__year = year 
		self.__isbn10 = isbn10
		self.__isbn13 = isbn13
		self.__edition = edition

	def __str__(self):
		return 'Title:     ' + self.title + '\n' + \
		       'Author(s): ' + ', '.join(self.authors) + '\n' \
				 'Publisher: ' + self.publisher + '\n' + \
				 'Year:      ' + self.year + '\n' + \
				 'ISBN-10:   ' + self.isbn10 + '\n' + \
				 'ISBN-13:   ' + self.isbn13 + '\n' + \
				 'Edition:   ' + self.edition

	def __get_title(self):
		return self.__title

	def __get_authors(self):
		return self.__authors
	
	def __get_publisher(self):
		return self.__publisher

	def __get_year(self):
		return self.__year

	def __get_isbn10(self):
		return self.__isbn10

	def __get_isbn13(self):
		return self.__isbn13

	def __get_edition(self):
		return self.__edition

	title = property(fget=__get_title)
	authors = property(fget=__get_authors)
	publisher = property(fget=__get_publisher)
	year = property(fget=__get_year)
	isbn10 = property(fget=__get_isbn10)
	isbn13 = property(fget=__get_isbn13)
	edition = property(fget=__get_edition)


class PyMazon:
	"""A method of looking up book information on Amazon."""
	def __init__(self, accesskey):
		self.__key = accesskey
		self.__last_query_time = 0

	def __form_request(self, isbn):
		return 'http://webservices.amazon.com/onca/xml?' + \
		       'Service=AWSECommerceService' + \
				 '&Version=2008-08-19' + \
		       '&AWSAccessKeyId=' + self.__key + \
				 '&Operation=ItemLookup' + \
				 '&ResponseGroup=ItemAttributes' + \
				 '&IdType=ISBN' + \
				 '&SearchIndex=Books' + \
				 '&ItemId=' + isbn

	def __elements_text(self, element, name):
		result = []
		matching = element.getElementsByTagName(name)
		for match in matching:
			if len(match.childNodes) != 1:
				continue
			child = match.firstChild
			if child.nodeType != Node.TEXT_NODE:
				continue
			result.append(child.nodeValue.strip())
		return result

	def __format_errors(self, errors):
		error_list = []
		for error in errors:
			error_list.extend(self.__elements_text(error, 'Message'))
		return error_list

	def __extract_single(self, element, name):
		matches = self.__elements_text(element, name)
		if len(matches) == 0:
			return ''
		return matches[0]

	def lookup(self, isbn):
		file = urllib.urlretrieve(self.__form_request(isbn))[0]
		xmldoc = minidom.parse(file)

		cur_time = time.time()
		while cur_time - self.__last_query_time < 1.0:
			sleep(cur_time - self.__last_query_time)
			cur_time = time.time()
		self.__last_query_time = cur_time

		errors = xmldoc.getElementsByTagName('Errors')
		if len(errors) != 0:
			raise PyMazonError, self.__format_errors(errors)

		title = self.__extract_single(xmldoc, 'Title')
		authors = self.__elements_text(xmldoc, 'Author')
		publisher = self.__extract_single(xmldoc, 'Publisher')
		year = self.__extract_single(xmldoc, 'PublicationDate')[0:4]
		isbn10 = self.__extract_single(xmldoc, 'ISBN')
		isbn13 = self.__extract_single(xmldoc, 'EAN')
		edition = self.__extract_single(xmldoc, 'Edition')

		return PyMazonBook(title, authors, publisher, year, isbn10, isbn13, edition)
