import sys, os
print('CWD:', os.getcwd())
print('sys.path:')
for p in sys.path:
    print(' -', p)
print('Exists categorizer.py?', os.path.exists('categorizer.py'))
print('Files in CWD:')
for f in os.listdir('.'):
    print(' -', f)
