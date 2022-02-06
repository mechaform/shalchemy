import os
import shalchemy as sha
from shalchemy import sh, bin
# There's a "smart" automatic command finder! It'll search your $PATH for you
from shalchemy.bin import cat, echo, grep, sort, mkdir


my_words = '''
zebra
banana
apple
frog
watermelon
xylophone
dolphin
yankee
carrot
elephant
'''.strip()

# This is equivalent to:
# echo $MY_WORDS | sort > words.txt
sha.run(echo([my_words]) | sort > 'words.txt')

# You can iterate over the result of an expression and it'll split by newlines
for word in cat('words.txt'):
    # You can cast expressions to str (or implicitly do so) to get the output of the command as a string
    print(f"Word: {echo(word) | sh('tr', '[a-z]', '[A-Z]')}")

# You can check if commands ran successfully by casting to bool or directly using it in a conditional
if (grep('-i', 'E') < 'words.txt') | grep('w'):
    print('Found it!')
else:
    print('It was not there!')

# You can directly use files (or other file-like objects) opened in Python as redirection targets!
with open('animals.txt', 'w+') as file:
    file.write('Beetle\nChimpanzee\nAardvark')
    file.seek(0)
    sha.run(sort < file)

sha.run(sh('rm', 'animals.txt'))

sha.run(mkdir('hello'))

os.chdir('hello')
sha.run(bin.pwd)

# '''
# curl website.com | sort > sorted.txt
# diff <(curl website.com) <(curl evilsite.com)

# # Output of both file commands get saved into a tempfile then diff reads both tempfiles
# diff <(curl website.com) <(curl evilsite.com)
# sh('diff', sh('curl website.com').read_sub, sh('curl evilsite.com').read_sub)

# # Input of both file commands come from tee then the output of both get flushed to tee's stdout
# cat words.txt | tee >(sort) >(sort -r)
# sh('cat words.txt') | sh('tee', sh('sort').wsub, sh('sort -r').wsub)

# cat <(curl https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/5d752e5f0702da315298a6bb5a771586d6ff445c/wordle-answers-alphabetical.txt) | tee >(sort) >(sort -r) > /dev/null

# cat words.txt | tee > /dev/null >(sort -r) >(sort) | cat
# '''
