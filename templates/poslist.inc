<!-- -*- html -*- -->
<table>
  {% for row in pos_rows %}
  <tr>
    <td>
      <a href='/addword/{{ row[0] }}'>{{ row[1] }}</a>
    </td>
  </tr>
  {% endfor %}
</table>
