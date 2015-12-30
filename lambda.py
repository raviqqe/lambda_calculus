#!/usr/bin/env python

import abc
import sys
import unicodedata



# constants

PUNCTUATIONS = {"\\", ".", "(", ")"}
DEBUG = True



# classes

## error

class Error:
  def __init__(self, pos, message, raw_message=False):
    if not raw_message:
      self.message = self.format_message(pos, message)
    else:
      self.message = message

  def __str__(self):
    return self.message

  def append_message(self, pos, message):
    return Error(pos, self.message + "\n" + self.format_message(pos, message),
                 raw_message=True)

  @staticmethod
  def format_message(pos, message):
    return "lambda:" + str(pos) + ": " + message


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
    return self


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
    def expression_parser(old_pos):
      result, pos = choice(self.term(),
                           self.bracketed(recursed(self.expression)))(old_pos)
      if isinstance(result, Error):
        debug_parser(old_pos, "expression failed.")
        return Error(old_pos, "An expression is expected."), old_pos
      debug_parser(pos, "expression parsed.")
      return result, pos
    return expression_parser

  def term(self):
    def term_parser(old_pos):
      result, pos = choice(self.variable(),
                           self.lambda_abstraction(),
                           self.function_application())(old_pos)
      if isinstance(result, Error):
        debug_parser(old_pos, "term failed.")
        return result.append_message(old_pos, "A term is expected."), old_pos
      debug_parser(pos, "term parsed.")
      return result, pos
    return term_parser

  def bracketed(self, parser):
    def bracketed_parser(old_pos):
      results, pos = sequence(self.punctuation("("),
                              parser,
                              self.punctuation(")"))(old_pos)
      if isinstance(results, Error):
        debug_parser(old_pos, "bracketed failed.")
        return results, old_pos
      debug_parser(pos, "bracketed parsed.")
      return results[1], pos
    return bracketed_parser

  def variable(self):
    def variable_parser(old_pos):
      result, pos = self.identifier()(old_pos)
      if isinstance(result, Error):
        debug_parser(old_pos, "variable failed.")
        return result.append_message(old_pos, "A variable is expected."), \
               old_pos
      debug_parser(pos, "variable parsed.")
      return Variable(result), pos

    return variable_parser

  def lambda_abstraction(self):
    def lambda_abstraction_parser(old_pos):
      results, pos = sequence(self.punctuation("\\"),
                              self.identifier(),
                              self.punctuation("."))(old_pos)
      if isinstance(results, Error):
        debug_parser(old_pos, "lambda abstraction failed.")
        return results.append_message(old_pos,
                                      "A lambda abstraction is expected."), \
               old_pos

      result, pos = self.expression()(pos)
      if isinstance(result, Error):
        debug_parser(old_pos, "lambda abstraction failed.")
        return result.append_message(old_pos, "An expression is expected."), \
               old_pos

      debug_parser(pos, "lambda abstraction parsed.")
      return LambdaAbstraction(results[1], result), pos

    return lambda_abstraction_parser

  def function_application(self):
    def function_application_parser(old_pos):
      result_1, pos = choice(self.variable(),
                             self.lambda_abstraction(),
                             self.bracketed(self.expression()))(old_pos)
      if isinstance(result_1, Error):
        debug_parser(old_pos, "function application failed.")
        return result_1.append_message(old_pos, "An expression is expected."),\
               old_pos

      result_2, pos = self.expression()(pos)
      if isinstance(result_2, Error):
        debug_parser(old_pos, "function application failed.")
        return result_2.append_message(old_pos, "An expression is expected."),\
               old_pos

      debug_parser(pos, "function application parsed.")
      return FunctionApplication(result_1, result_2), pos

    return function_application_parser

  def identifier(self):
    def identifier_parser(old_pos):
      _, pos = self.blanks()(old_pos)
      results, pos = sequence(self.letter(), many(self.letter()))(pos)
      if isinstance(results, Error):
        debug_parser(old_pos, "identifier failed.")
        return Error(old_pos, "An identifier is expected."), old_pos
      identifier = results[0] + "".join(results[1])
      debug_parser(pos, "identifier, \"{}\" parsed.".format(identifier))
      return identifier, pos

    return identifier_parser

  def punctuation(self, punctuation):
    assert punctuation in PUNCTUATIONS

    def punctuation_parser(old_pos):
      _, pos = self.blanks()(old_pos)
      if self.text[pos:pos+len(punctuation)] == punctuation:
        debug_parser(pos, "punctuation, {} parsed.".format(punctuation))
        return punctuation, pos + len(punctuation)
      debug_parser(old_pos, "punctuation, {} failed.".format(punctuation))
      return Error(old_pos,
                   "A punctuation, \"{}\" is expected.".format(punctuation)), \
             old_pos

    return punctuation_parser

  def blanks(self):
    def blanks_parser(old_pos):
      pos = old_pos
      while pos < len(self.text) and self.text[pos] in {" ", "\t", "\n"}:
        pos += 1
      return None, pos

    return blanks_parser

  def letter(self):
    def letter_parser(old_pos):
      pos = old_pos
      if len(self.text[pos:]) > 0 \
         and unicodedata.category(self.text[pos]).startswith("L"):
        return self.text[pos], pos + 1
      return Error(old_pos, "A letter is expected."), old_pos

    return letter_parser



# functions

def choice(*parsers):
  def choice_parser(old_pos):
    for parser in parsers:
      result, pos = parser(old_pos)
      if not isinstance(result, Error):
        return result, pos
    return Error(old_pos, "A choice parser failed."), old_pos
  return choice_parser


def sequence(*parsers):
  def sequence_parser(old_pos):
    pos = old_pos
    results = []
    for parser in parsers:
      result, pos = parser(pos)
      if isinstance(result, Error):
        return result, old_pos
      results.append(result)
    return results, pos
  return sequence_parser


def many(parser):
  def many_parser(old_pos):
    pos = old_pos
    results = []
    result, new_pos = parser(pos)
    while not isinstance(result, Error):
      results.append(result)
      pos = new_pos
      result, new_pos = parser(pos)
    return results, pos
  return many_parser


def recursed(parser_generator, *arguments):
  def recursed_parser(old_pos):
    return parser_generator(*arguments)(old_pos)
  return recursed_parser


def interpret(text):
  result = Parser().parse(text)
  if isinstance(result, Error):
    return result
  return result.eval({})


## utils

def usage():
  exit("usage: {} [<file>]".format(sys.argv[0]))


def debug(*messages):
  if DEBUG:
    print(*messages, file=sys.stderr)


def debug_parser(pos, *messages):
  if DEBUG:
    print(str(pos) + ":", *messages, file=sys.stderr)



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
