#!/usr/bin/env python

import abc
import sys
import unicodedata



# constants

PUNCTUATIONS = {"\\", "."}



# classes

## error

class Error:
  def __init__(self, message):
    self.message = message

  def __str__(self):
    return self.message

  def append_message(self, message):
    return Error(message + "\n" + self.message)


## AST

class AstNode(metaclass=abc.ABCMeta):
  @abc.abstractmethod
  def eval(self, env : dict):
    return NotImplemented

  @abc.abstractmethod
  def __str__(self):
    return NotImplemented


class Variable(AstNode):
  def __init__(self, name):
    self.name = name

  def __str__(self):
    return self.name

  def eval(self, env):
    if self.name in env:
      return env[self.name]
    return Error("A variable, \"{}\" is not defined.".format(self.name))


class LambdaAbstraction(AstNode):
  def __init__(self, argument : str, body):
    self.__argument = argument
    self.__body = body

  def __str__(self):
    return "\\" + self.argument + "." + str(self.__body)

  @property
  def argument(self):
    return self.__argument

  @property
  def body(self):
    return self.__body

  def eval(self, env):
    return self


class FunctionApplication(AstNode):
  def __init__(self, right_expression, left_expression):
    assert isinstance(right_expression, LambdaAbstraction)
    self.right_expression = right_expression
    self.left_expression = left_expression

  def __str__(self):
    return str(self.right_expression) + " " + str(self.left_expression)

  def eval(self, env):
    env[self.right_expression.argument] = left_expression.eval(env)
    return self.right_expression.body.eval(env)


## parser

class Parser:
  def parse(self, text):
    self.text = text
    result, _ = self.expression()(0)
    return result

  def expression(self):
    return self.term()

  def term(self):
    def term_parser(pos):
      result, pos = choice(self.variable(),
                           self.lambda_abstraction(),
                           self.function_application())(pos)
      if isinstance(result, Error):
        return result.append_message("A term is expected."), pos
      return result, pos
    return term_parser

  def variable(self):
    def variable_parser(pos):
      result, pos = self.identifier()(pos)
      if isinstance(result, Error):
        return result.append_message("A variable is expected."), pos
      return Variable(result), pos

    return variable_parser

  def lambda_abstraction(self):
    def lambda_abstraction_parser(pos):
      results, pos = sequence(self.punctuation("\\"),
                              self.identifier(),
                              self.punctuation("."))(pos)
      if isinstance(results, Error):
        return results.append_message("A lambda abstraction is expected."), pos

      result, pos = self.expression()(pos)
      if isinstance(result, Error):
        return result.append_message("An expression is expected."), pos

      return LambdaAbstraction(results[1], result), pos

    return lambda_abstraction_parser

  def function_application(self):
    def function_application_parser(pos):
      result_1, pos = self.expression()(pos)
      if isinstance(result_1, Error):
        return result_1.append_message("An expression is expected."), pos

      result_2, pos = self.expression()(pos)
      if isinstance(result_2, Error):
        return result_2.append_message("An expression is expected."), pos

      return FunctionApplication(result_1, result_2), pos

    return function_application_parser

  def identifier(self):
    def identifier_parser(old_pos):
      _, pos = self.blanks()(old_pos)
      results, pos = sequence(self.letter(), many(self.letter()))(pos)
      if isinstance(results, Error):
        return Error("An identifier is expected."), old_pos
      return results[0] + "".join(results[1]), pos

    return identifier_parser

  def punctuation(self, punctuation):
    assert punctuation in PUNCTUATIONS

    def punctuation_parser(pos):
      _, pos = self.blanks()(pos)
      if self.text[:len(punctuation)] == punctuation:
        return punctuation, pos + len(punctuation)
      return Error("A punctuation, \"{}\" is expected.".format(punctuation)), \
             pos

    return punctuation_parser

  def blanks(self):
    def blanks_parser(pos):
      while pos < len(self.text) and self.text[pos] in {" ", "\t", "\n"}:
        pos += 1
      return None, pos

    return blanks_parser

  def letter(self):
    def letter_parser(pos):
      if len(self.text[pos:]) > 0 \
         and unicodedata.category(self.text[pos]).startswith("L"):
        return self.text[pos], pos + 1
      return Error("A letter is expected."), pos

    return letter_parser



# functions

def choice(*parsers):
  def parser(pos):
    for parser in parsers:
      result, pos = parser(pos)
      if not isinstance(result, Error):
        return result, pos
    return result, pos
  return parser


def sequence(*parsers):
  def parser(old_pos):
    pos = old_pos
    results = []
    for parser in parsers:
      result, new_pos = parser(pos)
      if isinstance(result, Error):
        return result, pos
      pos = new_pos
      results.append(result)
    return results, pos
  return parser


def many(parser):
  def many_parser(pos):
    results = []
    result, new_pos = parser(pos)
    while not isinstance(result, Error):
      results.append(result)
      pos = new_pos
      result, new_pos = parser(pos)
    return results, pos
  return many_parser


def recursed(parser_generator, *arguments):
  def parser(pos):
    return parser_generator(*arguments)(pos)
  return parser


def interpret(text):
  return Parser().parse(text).eval({})


## utils

def usage():
  exit("usage: {} [<file>]".format(sys.argv[0]))



# main routine

def main():
  args = sys.argv[1:]

  if len(args) == 0:
    print(interpret(input()))
  elif len(args) == 1:
    with open(args[0]) as f:
      print(interpret(f.read()))
  else:
    usage()


if __name__ == "__main__":
  main()
