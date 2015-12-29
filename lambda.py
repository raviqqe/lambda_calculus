#!/usr/bin/env python

import abc
import sys



# constants

KEYWORDS = {"\\", "."}



# classes

## error

class Error:
  def __init__(self, message):
    self.message = message

  def __str__(self):
    return self.message

  def append_message(self, message):
    self.message = message + "\n" + self.message


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
    if name in env:
      return env[name]
    return Error("A variable, {} is not defined.".format(name))


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
    expression = self.expression() # DEBUG
    exit("OK") # DEBUG
    result, _ = self.expression()(0)
    return result

  def expression(self):
    return self.term()

  def term(self):
    def parser(pos):
      result, pos = choice(self.function_application(),
                           self.variable(),
                           self.lambda_abstraction())(pos)
      if isinstance(result, Error):
        return result.append_message("A term is expected."), pos
      return result, pos
    return parser

  def variable(self):
    def parser(pos):
      result, pos = self.identifier()(pos)
      if isinstance(result, Error):
        return result.append_message("A variable is expected."), pos
      return Variable(result), pos

    return parser

  def lambda_abstraction(self):
    def parser(pos):
      results, pos = sequence(self.keyword("\\"),
                              self.identifier(),
                              self.keyword("."))(pos)
      if isinstance(results, Error):
        return results.append_message("A lambda abstraction is expected."), pos

      result, pos = self.expression()(pos)
      if isinstance(result, Error):
        return result.append_message("An expression is expected."), pos

      return LambdaAbstraction(results[1], result), pos

    return parser

  def function_application(self):
    def parser(pos):
      result_1, pos = self.expression()(pos)
      if isinstance(result_1, Error):
        return result_1.append_message("An expression is expected."), pos

      result_2, pos = self.expression()(pos)
      if isinstance(result_2, Error):
        return result_2.append_message("An expression is expected."), pos

      return FunctionApplication(result_1, result_2), pos

    return parser

  def identifier(self):
    def parser(pos):
      _, pos = self.blanks()(pos)
      identifier = self.text[pos:].split()[0]
      if len(identifier) > 0 \
         and all(not identifier.startswith(keyword) for keyword in KEYWORDS):
        return identifier, pos + len(identifier)
      return Error("An identifier is expected."), pos

    return parser

  def keyword(self, keyword):
    assert keyword in KEYWORDS

    def parser(pos):
      _, pos = self.blanks()(pos)
      if self.text[:len(keyword)] == keyword:
        return keyword, pos + len(keyword)
      return Error("A keyword, \"{}\" is expected.".format(keyword)), pos

    return parser

  def blanks(self):
    def parser(pos):
      while self.text[pos] in {" ", "\t", "\n"}:
        pos += 1
      return None, pos

    return parser



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
  def parser(pos):
    results = []
    for parser in parsers:
      result, pos = parser(pos)
      if isinstance(result, Error):
        return result, pos
      results.append(result)
    return results, pos
  return parser


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
  usage()


if __name__ == "__main__":
  main()
