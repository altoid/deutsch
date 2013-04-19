<!-- -*- html -*- -->

<table>
  {% for d in quiz_list %}
  <tr>
    <td>
      <a href='/quizzes/{{ d['id'] }}'>{{ d['name'] }}</a>
    </td>
  </tr>
  {% endfor %}
</table>
