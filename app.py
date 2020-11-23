from flask import Flask, render_template, url_for, request, redirect, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import synth

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class Todo(db.Model):
 id = db.Column(db.Integer, primary_key=True)
 content = db.Column(db.String(200), nullable=False)
 date_created = db.Column(db.DateTime, default=datetime.utcnow)
 
 def ___repr__(self):
  return '<Task %r>' % self.id


def save_synth(phrase, file='audio.wav'):
    print(phrase)
    utt = synth.Utterance(phrase)
    diphone_synth = synth.Synth()
    diphone_synth.create_synthesis(utt.diphone_seq)
    diphone_synth.out.save(file)


@app.route('/', methods=['POST', 'GET'])
def index():
 if request.method == 'POST':
  if 'save' in request.form:
   task_content = request.form['content']
   new_task = Todo(content=task_content)
   try:
    db.session.add(new_task)
    db.session.commit()
    return redirect('/')
   except:
    return 'There was an issue saving your task'
  if 'play' in request.form:
    phrase = request.form['content']
    try:
        save_synth(phrase)
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', tasks=tasks, play=True, content=phrase)
    except:
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', tasks=tasks, play=False, error=True)
 else:
  tasks = Todo.query.order_by(Todo.date_created).all()
  return render_template('index.html', tasks=tasks, play=False)

@app.route('/delete/<int:id>')
def delete(id):
 task_to_delete = Todo.query.get_or_404(id)
 try:
  print(task_to_delete)
  db.session.delete(task_to_delete)
  db.session.commit()
  return redirect('/')
 except:
  return 'There was an issue deleting your task'

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
 task = Todo.query.get_or_404(id)
 if request.method == 'POST':
  task.content = request.form['content']
  try:
   db.session.commit()
   return redirect('/')
  except:
   return 'There was an issue updating your task'
 else:
  return render_template('update.html', task=task)

@app.route('/play/<int:id>')
def play(id):
  phrase = Todo.query.get_or_404(id)
  tasks = Todo.query.order_by(Todo.date_created).all()
  try:
    save_synth(phrase.content)
    return render_template('index.html', tasks=tasks, play=True)
  except:
      return render_template('index.html', tasks=tasks, error=True)


@app.route('/audio', methods=['GET'])
def send_audio():
    return send_file(
        "audio.wav",
        cache_timeout=0
    )


if __name__ == '__main__':
 app.run(debug=True,
         host='https://synthesizerr.herokuapp.com'
         )